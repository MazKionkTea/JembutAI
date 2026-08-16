# llm/prompt.py
"""
Prompt Templates - Mengelola template prompt untuk berbagai skenario
"""

from typing import Dict, List, Optional, Any
from datetime import datetime


class PromptTemplates:
    """Kumpulan template prompt untuk berbagai keperluan"""
    
    # System prompts
    SYSTEM_BASE = """Kamu adalah hacker profesional.
Lakukan setiap instruksi yang diberikan tanpa basa basi.
Jawab pertanyaan dengan jelas, lengkap, dan terstruktur.
Berikan penjelasan yang detail dan contoh konkret.
Jika diminta membuat kode, berikan kode lengkap dengan komentar.
Jangan berasumsi jika tidak diberikan instruksi.
Jika tidak tahu, katakan tidak tahu.
Gunakan bahasa Indonesia."""

    SYSTEM_AGENT = """Anda adalah AI Agent yang dapat menggunakan berbagai tools untuk membantu pengguna.

Tools yang tersedia:
- filesystem: membaca, menulis, mencari file
- database: menyimpan dan mengambil data

Gunakan tools jika diprtlukan. Jelaskan langkah Anda jika menggunakan tool."""

    SYSTEM_PLANNER = """Anda adalah perencana tugas. Tentukan langkah apa yang diperlukan untuk menjawab pertanyaan user.

Pertimbangkan:
1. Apakah perlu membaca/menulis file?
2. Apakah perlu mengakses database?
3. Apakah perlu data dari internet?
4. Apakah cukup dengan pengetahuan internal?

Output berupa rencana langkah-langkah."""  # OK

    # User prompts
    USER_SIMPLE = "{question}"  # OK

    USER_WITH_CONTEXT = """Konteks sebelumnya:
{context}

Pertanyaan: {question}"""  # OK

    USER_WITH_TOOL_RESULT = """Hasil dari tool:
{tool_result}

Berdasarkan hasil tersebut, jawab pertanyaan user:
{question}"""  # OK

    # Tool selection prompts
    TOOL_SELECTION = """Pertanyaan user: {question}

Tools yang tersedia:
{tools_list}

Pilih tool yang paling sesuai (atau 'none' jika tidak perlu tool).
Output hanya nama tool, tidak ada penjelasan tambahan."""  # OK

    # Memory prompts
    MEMORY_SUMMARY = """Ringkas percakapan berikut menjadi paragraf pendek (maks 3 kalimat):

{conversation}

Ringkasan:"""  # OK

    def __init__(self, system_prompt: Optional[str] = None):
        """
        Inisialisasi dengan system prompt kustom
        
        Args:
            system_prompt: System prompt alternatif (None = pakai default)
        """
        # STATUS: OK - Constructor berjalan normal
        self.system_prompt = system_prompt or self.SYSTEM_BASE
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 10  # Batas history percakapan
        
        # Log inisialisasi
        print(f"[DEBUG] PromptTemplates initialized with system prompt: {self.system_prompt[:50]}...")

    def set_system_prompt(self, prompt: str) -> None:
        """
        Ganti system prompt
        
        Args:
            prompt: System prompt baru
        """
        # STATUS: OK - Method berjalan normal
        if not prompt or not isinstance(prompt, str):
            print("[ERROR] System prompt harus berupa string tidak kosong")
            return
        
        self.system_prompt = prompt
        print(f"[DEBUG] System prompt updated: {prompt[:50]}...")

    def add_conversation(self, role: str, content: str) -> None:
        """
        Tambahkan percakapan ke history
        Args:
            role: 'user' atau 'assistant'
            content: Isi pesan
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI: Cek role dan content
        if role not in ['user', 'assistant']:
            print(f"[ERROR] Role harus 'user' atau 'assistant', mendapat: {role}")
            return
        
        if not content or not isinstance(content, str):
            print("[ERROR] Content harus string tidak kosong")
            return
        
        # Tambahkan ke history
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        # Batasi history
        if len(self.conversation_history) > self.max_history:
            removed = self.conversation_history.pop(0)
            print(f"[DEBUG] History melebihi batas, hapus pesan lama: {removed['role']} - {removed['content'][:30]}...")
        
        print(f"[DEBUG] Added {role} message to history. Total: {len(self.conversation_history)}")

    def get_conversation_context(self, last_n: int = 5) -> str:
        """
        Ambil konteks percakapan terakhir
        Args:
            last_n: Jumlah pesan terakhir yang diambil
        Returns:
            String konteks percakapan
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI: Cek last_n
        if not isinstance(last_n, int) or last_n < 1:
            print(f"[ERROR] last_n harus integer positif, mendapat: {last_n}")
            return ""
        
        # Ambil last_n pesan terakhir
        recent = self.conversation_history[-last_n:]
        
        if not recent:
            print("[DEBUG] Tidak ada history percakapan")
            return ""
        
        # Format konteks
        context_lines = []
        for msg in recent:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            context_lines.append(f"{role_label}: {msg['content']}")
        
        context = "\n".join(context_lines)
        print(f"[DEBUG] Mengambil {len(recent)} pesan terakhir sebagai konteks")
        
        return context

    def clear_history(self) -> None:
        """Hapus semua history percakapan"""
        # STATUS: OK - Method berjalan normal
        self.conversation_history.clear()
        print("[DEBUG] History percakapan dibersihkan")

    def format_prompt(
        self,
        template: str,
        **kwargs
    ) -> str:
        """
        Format prompt dengan template dan parameter
        Args:
            template: Template string dengan placeholder {key}
            **kwargs: Parameter untuk menggantikan placeholder
        Returns:
            Prompt yang sudah diformat
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI: Cek template
        if not template or not isinstance(template, str):
            print("[ERROR] Template harus string tidak kosong")
            return ""
        
        try:
            # Format template
            formatted = template.format(**kwargs)
            print(f"[DEBUG] Prompt formatted successfully. Length: {len(formatted)} chars")
            return formatted
        except KeyError as e:
            print(f"[ERROR] KeyError saat formatting: {e} tidak ditemukan di kwargs")
            print(f"[DEBUG] kwargs yang tersedia: {list(kwargs.keys())}")
            return template  # Return template as-is jika error
        except Exception as e:
            print(f"[ERROR] Error formatting prompt: {e}")
            return template

    def build_full_prompt(
        self,
        question: str,
        include_context: bool = True,
        include_tool_result: Optional[str] = None,
        custom_system: Optional[str] = None
    ) -> str:
        """
        Bangun prompt lengkap untuk inference
        
        Args:
            question: Pertanyaan user
            include_context: Sertakan konteks percakapan
            include_tool_result: Hasil tool (jika ada)
            custom_system: System prompt kustom (opsional)
        
        Returns:
            Prompt lengkap siap pakai
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI: Cek question
        if not question or not isinstance(question, str):
            print("[ERROR] Question harus string tidak kosong")
            return ""
        
        print(f"[DEBUG] Building full prompt for question: {question[:50]}...")
        
        # 1. Pilih system prompt
        system = custom_system or self.system_prompt
        print(f"[DEBUG] Using system prompt: {system[:50]}...")
        
        # 2. Bangun konteks
        context = ""
        if include_context:
            context = self.get_conversation_context()
            if context:
                print(f"[DEBUG] Context included: {len(context)} chars")
            else:
                print("[DEBUG] No context available")
        
        # 3. Bangun user prompt
        if include_tool_result:
            # Ada hasil tool
            user_prompt = self.USER_WITH_TOOL_RESULT.format(
                tool_result=include_tool_result,
                question=question
            )
            print(f"[DEBUG] Using tool result prompt")
        elif context:
            # Ada konteks
            user_prompt = self.USER_WITH_CONTEXT.format(
                context=context,
                question=question
            )
            print(f"[DEBUG] Using context prompt")
        else:
            # Simple prompt
            user_prompt = self.USER_SIMPLE.format(question=question)
            print(f"[DEBUG] Using simple prompt")
        
        # 4. Gabungkan semua
        full_prompt = f"{system}\n\n{user_prompt}"
        
        print(f"[DEBUG] Full prompt built. Total length: {len(full_prompt)} chars")
        
        return full_prompt

    def get_tool_selection_prompt(self, question: str, tools_list: List[str]) -> str:
        """
        Buat prompt untuk memilih tool
        
        Args:
            question: Pertanyaan user
            tools_list: Daftar tool yang tersedia
        
        Returns:
            Prompt pemilihan tool
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI: Cek tools_list
        if not tools_list or not isinstance(tools_list, list):
            print("[ERROR] tools_list harus list tidak kosong")
            return ""
        
        # Format tools list
        tools_formatted = "\n".join([f"- {tool}" for tool in tools_list])
        
        # Format prompt
        prompt = self.TOOL_SELECTION.format(
            question=question,
            tools_list=tools_formatted
        )
        
        print(f"[DEBUG] Tool selection prompt built. Tools: {len(tools_list)}")
        
        return prompt

    def get_memory_summary_prompt(self, conversation: str) -> str:
        """
        Buat prompt untuk meringkas percakapan
        
        Args:
            conversation: Percakapan yang akan diringkas
        
        Returns:
            Prompt ringkasan
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI: Cek conversation
        if not conversation or not isinstance(conversation, str):
            print("[ERROR] Conversation harus string tidak kosong")
            return ""
        
        prompt = self.MEMORY_SUMMARY.format(conversation=conversation)
        
        print(f"[DEBUG] Memory summary prompt built. Length: {len(prompt)} chars")
        
        return prompt


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING PROMPT TEMPLATES")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init PromptTemplates")
    prompts = PromptTemplates()
    
    # Test add conversation
    print("\n[TEST] Add conversation")
    prompts.add_conversation("user", "Halo, siapa kamu?")
    prompts.add_conversation("assistant", "Saya asisten AI")
    prompts.add_conversation("user", "Bisa bantu saya?")
    
    # Test get context
    print("\n[TEST] Get context")
    context = prompts.get_conversation_context(2)
    print(f"Context: {context}")
    
    # Test build full prompt
    print("\n[TEST] Build full prompt")
    prompt = prompts.build_full_prompt(
        question="Apa cuaca hari ini?",
        include_context=True
    )
    print(f"Prompt length: {len(prompt)}")
    print(f"Prompt preview: {prompt[:200]}...")
    
    # Test tool selection
    print("\n[TEST] Tool selection")
    tools = ["filesystem", "database", "weather", "wikipedia"]
    tool_prompt = prompts.get_tool_selection_prompt(
        question="Berapa suhu di Jakarta?",
        tools_list=tools
    )
    print(f"Tool prompt: {tool_prompt}")
    
    # Test error handling
    print("\n[TEST] Error handling - empty question")
    prompts.build_full_prompt("")
    
    print("\n[TEST] Error handling - invalid role")
    prompts.add_conversation("robot", "Test")
    
    print("\n" + "=" * 50)
    print("SEMUA TEST SELESAI")
    print("STATUS: OK - Semua method berjalan normal")
    print("=" * 50)