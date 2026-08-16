# llm/inference.py
"""
Inference Engine - Mengelola inferensi model dan menghasilkan respons
"""

from typing import Optional, List, Dict, Any, Generator, Union
from datetime import datetime
import json
import time

from llm.loader import LLMLoader
from llm.prompt import PromptTemplates


class InferenceEngine:
    """Engine untuk melakukan inferensi dengan model LLM"""
    
    def __init__(
        self,
        loader: LLMLoader,
        prompt_templates: Optional[PromptTemplates] = None,
        max_tokens: int = 100000,
        temperature: float = 0.2,
        top_p: float = 0.95,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        stop_strings: Optional[List[str]] = None,
        stream: bool = False,
        verbose: bool = False
    ):
        if not isinstance(loader, LLMLoader):
            print("[ERROR] loader harus instance dari LLMLoader")
            raise TypeError("loader must be LLMLoader instance")
        
        if not loader.is_loaded:
            print("[ERROR] Model belum dimuat. Panggil loader.load() terlebih dahulu")
            raise RuntimeError("Model not loaded. Call loader.load() first")
        
        self.loader = loader
        self.model = loader.get_model()
        self.prompt_templates = prompt_templates or PromptTemplates()
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repeat_penalty = repeat_penalty
        self.stop_strings = stop_strings or ["<|im_end|>"]
        self.stream = stream
        self.verbose = verbose
        
        self.total_tokens = 0
        self.total_requests = 0
        self.average_latency = 0.0
        
        if self.verbose:
            print(f"[DEBUG] InferenceEngine initialized")
            print(f"[DEBUG] Config: max_tokens={max_tokens}, temp={temperature}, stream={stream}")

    def _parse_prompt_to_messages(self, prompt: str) -> List[Dict[str, str]]:
        """
        Parse prompt string menjadi format messages untuk chat completion
        
        Args:
            prompt: Prompt string (format: "SYSTEM\n\nUSER" atau plain)
        
        Returns:
            List messages [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
        """
        messages = []
        
        # Cek apakah ada system prompt
        if "\n\n" in prompt:
            parts = prompt.split("\n\n", 1)
            # Cek apakah bagian pertama adalah system prompt (mengandung kata kunci)
            if "Anda adalah" in parts[0] or "asisten" in parts[0] or "ATURAN" in parts[0]:
                messages.append({"role": "system", "content": parts[0].strip()})
                user_content = parts[1].strip() if len(parts) > 1 else ""
            else:
                user_content = prompt
        else:
            user_content = prompt
        
        if user_content:
            messages.append({"role": "user", "content": user_content})
        
        # Jika tidak ada system prompt, tambahkan default
        if not messages:
            messages = [
                {"role": "system", "content": "Anda adalah asisten AI yang membantu, jujur, dan aman. Jawab pertanyaan dengan jelas dan akurat. Gunakan bahasa Indonesia."},
                {"role": "user", "content": prompt}
            ]
        
        return messages

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        stop_strings: Optional[List[str]] = None,
        stream: Optional[bool] = None,
        echo: bool = False
    ) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """Generate respons dari prompt"""
        if not prompt or not isinstance(prompt, str):
            print("[ERROR] Prompt harus string tidak kosong")
            return {
                'text': '',
                'error': 'Prompt tidak valid',
                'tokens': 0,
                'latency': 0.0
            }
        
        if self.verbose:
            print(f"[DEBUG] Generating response for prompt: {prompt[:100]}...")
        
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        top_p = top_p or self.top_p
        top_k = top_k or self.top_k
        repeat_penalty = repeat_penalty or self.repeat_penalty
        stop_strings = stop_strings or self.stop_strings
        stream = stream if stream is not None else self.stream
        
        if self.verbose:
            print(f"[DEBUG] Parameters: max_tokens={max_tokens}, temp={temperature}")
        
        start_time = time.time()
        
        try:
            # Parse prompt ke messages
            messages = self._parse_prompt_to_messages(prompt)
            
            if self.verbose:
                print(f"[DEBUG] Messages: {len(messages)} messages")
            
            if stream:
                if self.verbose:
                    print("[DEBUG] Using streaming mode")
                return self._generate_stream_chat(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repeat_penalty=repeat_penalty,
                    stop_strings=stop_strings
                )
            else:
                if self.verbose:
                    print("[DEBUG] Using batch mode")
                
                response = self.model.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repeat_penalty=repeat_penalty,
                    stop=stop_strings,
                    stream=False
                )
                
                latency = time.time() - start_time
                
                # Ekstrak hasil dari chat completion
                text = ''
                tokens = 0
                
                if isinstance(response, dict):
                    choices = response.get('choices', [])
                    if choices:
                        message = choices[0].get('message', {})
                        if isinstance(message, dict):
                            text = message.get('content', '')
                    usage = response.get('usage', {})
                    if isinstance(usage, dict):
                        tokens = usage.get('total_tokens', 0)
                
                self.total_tokens += tokens
                self.total_requests += 1
                self.average_latency = (
                    (self.average_latency * (self.total_requests - 1) + latency) 
                    / self.total_requests
                )
                
                if self.verbose:
                    print(f"[DEBUG] Response generated. Tokens: {tokens}, Latency: {latency:.2f}s")
                
                return {
                    'text': text.strip(),
                    'tokens': tokens,
                    'latency': latency,
                    'total_tokens': self.total_tokens,
                    'total_requests': self.total_requests,
                    'avg_latency': self.average_latency,
                    'error': None
                }
                
        except Exception as e:
            print(f"[ERROR] Error generating response: {e}")
            return {
                'text': '',
                'error': str(e),
                'tokens': 0,
                'latency': time.time() - start_time
            }

    def _generate_stream_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
        repeat_penalty: float,
        stop_strings: List[str]
    ) -> Generator[Dict[str, Any], None, None]:
        """Generate response secara streaming dengan format chat"""
        if self.verbose:
            print("[DEBUG] Starting chat stream generation")
        
        start_time = time.time()
        full_text = ""
        chunk_count = 0
        
        try:
            for chunk in self.model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repeat_penalty=repeat_penalty,
                stop=stop_strings,
                stream=True
            ):
                chunk_text = ''
                if isinstance(chunk, dict):
                    choices = chunk.get('choices', [])
                    if choices:
                        delta = choices[0].get('delta', {})
                        if isinstance(delta, dict):
                            chunk_text = delta.get('content', '')
                
                if chunk_text:
                    full_text += chunk_text
                    chunk_count += 1
                    
                    yield {
                        'text': chunk_text,
                        'full_text': full_text,
                        'chunk': chunk_count,
                        'is_last': False
                    }
            
            latency = time.time() - start_time
            tokens = len(full_text.split())
            
            self.total_tokens += tokens
            self.total_requests += 1
            self.average_latency = (
                (self.average_latency * (self.total_requests - 1) + latency) 
                / self.total_requests
            )
            
            yield {
                'text': '',
                'full_text': full_text,
                'chunk': chunk_count,
                'is_last': True,
                'tokens': tokens,
                'latency': latency
            }
            
            if self.verbose:
                print(f"[DEBUG] Stream complete. Chunks: {chunk_count}, Latency: {latency:.2f}s")
            
        except Exception as e:
            print(f"[ERROR] Error in chat stream generation: {e}")
            yield {
                'text': '',
                'full_text': full_text,
                'error': str(e),
                'is_last': True
            }

    def generate_response(
        self,
        pertanyaan: str,
        konteks: Optional[str] = None,
        tool_result: Optional[str] = None,
        custom_system: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate respons untuk pertanyaan user dengan konteks"""
        if self.verbose:
            print(f"[DEBUG] Generating response for question: {pertanyaan[:50]}...")
        
        # FORCE max_tokens = 4096 jika tidak di-set
        if 'max_tokens' not in kwargs:
            kwargs['max_tokens'] = 10000
            if self.verbose:
                print(f"[DEBUG] Force max_tokens: {kwargs['max_tokens']}")
        
        prompt = self.prompt_templates.build_full_prompt(
            question=pertanyaan,
            include_context=bool(konteks or self.prompt_templates.conversation_history),
            include_tool_result=tool_result,
            custom_system=custom_system
        )
        
        if not prompt:
            print("[ERROR] Gagal membangun prompt")
            return {
                'text': '',
                'error': 'Failed to build prompt',
                'tokens': 0,
                'latency': 0.0
            }
        
        print(f"[DEBUG] generate_response received max_tokens: {kwargs.get('max_tokens')}") 
        result = self.generate(prompt, **kwargs)
        
        if isinstance(result, Generator):
            print("[ERROR] generate_response tidak mendukung streaming")
            return {
                'text': '',
                'error': 'Streaming tidak didukung di generate_response',
                'tokens': 0,
                'latency': 0.0
            }
        
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            'total_requests': self.total_requests,
            'total_tokens': self.total_tokens,
            'average_latency': self.average_latency,
            'model': str(self.loader.model_path),
            'config': {
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'top_p': self.top_p,
                'top_k': self.top_k
            }
        }

    def reset_stats(self) -> None:
        self.total_tokens = 0
        self.total_requests = 0
        self.average_latency = 0.0
        if self.verbose:
            print("[DEBUG] Stats reset")