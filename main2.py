#!/usr/bin/env python3

"""
Aplikasi chat interaktif dengan model GGUF di CPU.

Mendukung berbagai format prompt (Llama 2/3, Mistral, Qwen, ChatML).
Default: Qwen.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from llama_cpp import Llama
from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

# ---------- Konfigurasi default ----------
try:
    import multiprocessing

    _DEFAULT_THREADS = multiprocessing.cpu_count()
except Exception:
    _DEFAULT_THREADS = 4

DEFAULT_CONFIG: Dict = {
    "max_tokens": 1024,
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "n_ctx": 1024,
    "threads": _DEFAULT_THREADS,
    "stream": True,
    "reasoning": True,
    "system_prompt": "Anda adalah asisten AI yang membantu, ramah, dan memberikan jawaban yang informatif.",
    "prompt_format": "qwen",
}

console = Console()

# ---------- Formatter prompt ----------
FormatFn = Callable[[str, str], str]

PROMPT_FORMATTERS: Dict[str, FormatFn] = {
    "llama2": lambda sys, usr: (
        f"[INST] <<SYS>>\n{sys}\n<</SYS>>\n\n{usr} [/INST]"
    ),
    "llama3": lambda sys, usr: (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{sys}"
        f"<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{usr}"
        f"<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    ),
    "mistral": lambda sys, usr: f"<s>[INST] {sys}\n\n{usr} [/INST]",
    "qwen": lambda sys, usr: (
        f"<|im_start|>system\n{sys}<|im_end|>\n"
        f"<|im_start|>user\n{usr}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    ),
    "chatml": lambda sys, usr: (
        f"<|im_start|>system\n{sys}<|im_end|>\n"
        f"<|im_start|>user\n{usr}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    ),
}
# Qwen dan ChatML identik secara struktural; pastikan hanya satu definisi aktual
PROMPT_FORMATTERS["chatml"] = PROMPT_FORMATTERS["qwen"]

STOP_TOKENS: Dict[str, List[str]] = {
    "qwen": ["<|im_end|>", "<|im_start|>"],
    "chatml": ["<|im_end|>", "<|im_start|>"],
    "llama3": ["<|eot_id|>", "<|start_header_id|>"],
    "llama2": ["</s>", "[INST]"],
    "mistral": ["</s>", "[INST]"],
}

_DETECTION_RULES: List[tuple] = [
    ("llama3", ["llama-3", "llama3", "llama 3"]),
    ("llama2", ["llama-2", "llama2", "llama 2"]),
    ("qwen", ["qwen"]),
    ("mistral", ["mistral", "mixtral"]),
    ("chatml", ["chatml", "hermes", "zephyr", "openchat", "dolphin"]),
    ("llama2", ["llama"]),
]


class PromptFormatter:
    @staticmethod
    def detect_format(model_path: str) -> str:
        name = os.path.basename(model_path).lower()
        for fmt, keywords in _DETECTION_RULES:
            if any(k in name for k in keywords):
                return fmt
        return "llama2"

    @staticmethod
    def build_prompt(system: str, user: str, fmt: str) -> str:
        fn = PROMPT_FORMATTERS.get(fmt) or PROMPT_FORMATTERS["llama2"]
        return fn(system, user)

    @staticmethod
    def get_stop_tokens(fmt: str) -> List[str]:
        return STOP_TOKENS.get(fmt, ["</s>"])


# ---------- Utilitas Pemilih Model ----------
def resolve_model_path(raw_path: str) -> Optional[str]:
    """Memproses path input. Jika direktori, cari file .gguf dan minta user memilih."""
    raw_path = os.path.expanduser(raw_path)
    if os.path.isfile(raw_path) and raw_path.lower().endswith(".gguf"):
        return raw_path
    if os.path.isdir(raw_path):
        console.print(f"[cyan]Memindai direktori untuk file .gguf...[/cyan]")
        gguf_files = sorted([f for f in os.listdir(raw_path) if f.lower().endswith(".gguf")])
        if not gguf_files:
            console.print(f"[red]Tidak ada file .gguf ditemukan di: {raw_path}[/red]")
            return None
        if len(gguf_files) == 1:
            return os.path.join(raw_path, gguf_files[0])
        console.print("[bold cyan]Ditemukan beberapa model. Pilih salah satu:[/bold cyan]")
        for i, f in enumerate(gguf_files, start=1):
            console.print(f"  [yellow]{i}.[/yellow] {f}")
        choice = Prompt.ask("Pilih nomor model", choices=[str(i) for i in range(1, len(gguf_files) + 1)])
        return os.path.join(raw_path, gguf_files[int(choice) - 1])
    console.print(f"[red]Path tidak valid atau bukan file .gguf: {raw_path}[/red]")
    return None


# ---------- Deteksi Tombol Stop (Enter) ----------
def check_stop() -> bool:
    """Cek apakah user menekan Enter (untuk menghentikan generasi)."""
    if sys.platform == "win32":
        try:
            import msvcrt

            if msvcrt.kbhit():
                ch = msvcrt.getch()
                # Hanya anggap stop kalau Enter (\\r). Key lain diabaikan.
                if ch in (b"\\r", b"\\n"):
                    return True
                # Key lain: sudah di-consume, jangan trigger stop
                return False
        except ImportError:
            pass
    else:
        try:
            import select

            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                # Baca satu baris (Enter). Karakter non-newline lain akan terbaca
                # sebagai bagian baris dan ikut ter-consume.
                sys.stdin.readline()
                return True
        except Exception:
            pass
    return False


# ---------- Definisi parameter untuk menu ----------
@dataclass
class ParamSpec:
    key: str
    label: str
    cast: Callable[[str], object]
    validator: Optional[Callable[[object], bool]] = None
    needs_reload: bool = False
    help_text: str = ""

    def ask_and_update(self, config: Dict) -> bool:
        default = str(config[self.key])
        raw = Prompt.ask(self.label, default=default)
        try:
            val = self.cast(raw)
        except ValueError:
            console.print("[red]Input tidak valid (format salah).[/red]")
            return False
        if self.validator and not self.validator(val):
            console.print(f"[red]Nilai tidak valid: {self.help_text}[/red]")
            return False
        config[self.key] = val
        reload_msg = " Reload diperlukan." if self.needs_reload else ""
        console.print(f"[green]✓ Diperbarui.{reload_msg}[/green]")
        return True


def _is_int_pos(v: int) -> bool:
    return v > 0


def _is_int_nonneg(v: int) -> bool:
    return v >= 0  # 0 = disabled (dipakai top_k)


def _is_temp(v: float) -> bool:
    return 0.0 <= v <= 2.0


def _is_prob(v: float) -> bool:
    return 0.0 < v <= 1.0


def _is_penalty(v: float) -> bool:
    return v >= 1.0


PARAM_SPECS: List[ParamSpec] = [
    ParamSpec("max_tokens", "max_tokens", int, _is_int_pos, help_text="harus > 0"),
    ParamSpec("temperature", "temperature (0.0-2.0)", float, _is_temp, help_text="0.0-2.0"),
    ParamSpec("top_p", "top_p (0.0-1.0)", float, _is_prob, help_text="0.0-1.0"),
    ParamSpec("top_k", "top_k (0 = disabled)", int, _is_int_nonneg, help_text=">= 0 (0 = disabled)"),
    ParamSpec("repeat_penalty", "repeat_penalty (>=1.0)", float, _is_penalty, help_text=">= 1.0"),
    ParamSpec("n_ctx", "n_ctx", int, _is_int_pos, needs_reload=True, help_text="harus > 0"),
    ParamSpec("threads", "threads", int, _is_int_pos, needs_reload=True, help_text="harus > 0"),
]


# ---------- Kelas Aplikasi ----------
class ChatApp:
    def __init__(self, model_path: str, prompt_format: str = "auto", reasoning: bool = True):
        self.model_path = model_path
        self.config = DEFAULT_CONFIG.copy()
        self.config["prompt_format"] = (
            PromptFormatter.detect_format(model_path)
            if prompt_format == "auto"
            else prompt_format
        )
        self.config["reasoning"] = reasoning
        self.model: Optional[Llama] = None
        self.running = True
        # Track apakah user set format eksplisit via --format. Kalau ya, change_model
        # tidak boleh override auto-detect dari nama file.
        self._explicit_format: bool = (prompt_format != "auto")

    # --- model ---
    def _cleanup_model(self) -> None:
        if self.model is not None:
            # Pakai close() eksplisit kalau tersedia, supaya native resource
            # (llama_context, llama_model) dilepas deterministic, bukan menunggu GC.
            try:
                close = getattr(self.model, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass
            try:
                del self.model
            except Exception:
                pass
        self.model = None

    def load_model(self) -> bool:
        self._cleanup_model()
        try:
            console.print(f"[bold cyan]Memuat model[/bold cyan] dari {self.model_path} ...")
            console.print(
                f"[dim]Threads: {self.config['threads']}, "
                f"Konteks: {self.config['n_ctx']}, "
                f"Format: {self.config['prompt_format']}[/dim]"
            )
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.config["n_ctx"],
                n_threads=self.config["threads"],
                n_gpu_layers=0,
                verbose=False,
            )
            console.print("[bold green]✓ Model siap![/bold green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Error memuat model: {e}[/bold red]")
            return False

    def change_model(self) -> None:
        current_dir = os.path.dirname(self.model_path) or "."
        new_dir = Prompt.ask("Masukkan path direktori (atau file .gguf spesifik)", default=current_dir)
        new_path = resolve_model_path(new_dir)
        if not new_path:
            return
        # Snapshot state lama agar bisa rollback kalau reload gagal
        old_path = self.model_path
        old_format = self.config["prompt_format"]
        self.model_path = new_path
        # Hanya auto-detect format dari nama file kalau user TIDAK set --format eksplisit
        if not self._explicit_format:
            self.config["prompt_format"] = PromptFormatter.detect_format(self.model_path)
        console.print(f"[green]Model diubah ke: {os.path.basename(self.model_path)}[/green]")
        if Confirm.ask("Reload model sekarang?", default=True):
            if not self.load_model():
                # Kembalikan state supaya UI tidak nyangkut di path/format yang gagal
                self.model_path = old_path
                self.config["prompt_format"] = old_format
                console.print("[red]Gagal reload. Path & format dikembalikan.[/red]")

    # --- prompt & completion ---
    def _build_prompt(self, user_input: str) -> str:
        system = self.config["system_prompt"]
        user = user_input
        if not self.config["reasoning"]:
            if self.config["prompt_format"] in ("qwen", "chatml"):
                # Qwen3: /no_think adalah slash command di USER message, bukan system.
                # Diletakkan di awal pesan user (sebelum konten) agar dikenali tokenizer.
                if not user.lstrip().startswith("/no_think"):
                    user = "/no_think " + user
            else:
                system += "\n\nInstruksi: Jawab pertanyaan secara langsung tanpa menampilkan proses berpikir."
        return PromptFormatter.build_prompt(system, user, self.config["prompt_format"])

    def _completion_kwargs(self, prompt: str, stream: bool) -> Dict:
        return {
            "prompt": prompt,
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
            "top_p": self.config["top_p"],
            "top_k": self.config["top_k"],
            "repeat_penalty": self.config["repeat_penalty"],
            "stream": stream,
            "stop": PromptFormatter.get_stop_tokens(self.config["prompt_format"]),
            "echo": False,
        }

    def stream_generate(self, prompt: str):
        full_prompt = self._build_prompt(prompt)
        hide_think = not self.config["reasoning"]
        buffer = ""
        in_think = False
        # Konstanta tag thinking Qwen
        TAG_OPEN = "<think>"
        TAG_CLOSE = "</think>"
        LEN_OPEN = len(TAG_OPEN)  # 7
        LEN_CLOSE = len(TAG_CLOSE)  # 8
        MAX_TAG_LEN = max(LEN_OPEN, LEN_CLOSE)  # 8
        BUF_LIMIT = 256  # batas atas buffer agar tidak membengkak tanpa kendali

        def _longest_partial_tag_suffix(buf: str) -> str:
            """Cari suffix terpanjang dari buf yang masih berupa prefix TAG_OPEN/TAG_CLOSE.
            Return '' kalau tidak ada. Mis. 'hi</thin' -> '</thin', 'abc<think>' -> '<think>'."""
            for length in range(min(MAX_TAG_LEN, len(buf)), 0, -1):
                sub = buf[-length:]
                if TAG_OPEN.startswith(sub) or TAG_CLOSE.startswith(sub):
                    return sub
            return ""

        def _safe_truncate(buf: str) -> str:
            """Truncate buffer dari depan tanpa memotong tag yang sedang di-buffer.
            Hanya membuang karakter yang jelas bukan awalan tag manapun."""
            if len(buf) <= BUF_LIMIT:
                return buf
            for cut in range(1, len(buf) - MAX_TAG_LEN + 1):
                if not _longest_partial_tag_suffix(buf[cut:]):
                    return buf[cut:]
            # Fallback: hard-truncate ke BUF_LIMIT dari belakang
            return buf[-BUF_LIMIT:]

        for chunk in self.model.create_completion(**self._completion_kwargs(full_prompt, True)):
            token = chunk["choices"][0]["text"]
            if not token:
                continue
            # Jika reasoning off, filter tag thinking agar tidak tampil di UI
            if not hide_think:
                yield token
                continue

            buffer += token
            while True:
                if in_think:
                    end_idx = buffer.find(TAG_CLOSE)
                    if end_idx != -1:
                        buffer = buffer[end_idx + LEN_CLOSE:]
                        in_think = False
                    else:
                        buffer = _safe_truncate(buffer)
                        break
                else:
                    start_idx = buffer.find(TAG_OPEN)
                    if start_idx != -1:
                        # Yield semua sebelum tag, lalu masuk mode in_think
                        if start_idx > 0:
                            yield buffer[:start_idx]
                        buffer = buffer[start_idx + LEN_OPEN:]
                        in_think = True
                    else:
                        # Yield sebanyak-banyak yang aman. Pisahkan pada partial-tag suffix
                        # terpanjang agar tidak bocor ke user. Mis. 'hi</thin' -> yield 'hi',
                        # simpan '</thin' untuk iterasi berikut.
                        partial = _longest_partial_tag_suffix(buffer)
                        if partial:
                            keep = len(partial)
                            yieldable = buffer[:-keep] if len(buffer) > keep else ""
                            if yieldable:
                                yield yieldable
                            buffer = partial
                        else:
                            if buffer:
                                yield buffer
                            buffer = ""
                        break

        # Sisa buffer akhir: yield hanya jika BUKAN partial-tag suffix.
        if not in_think and buffer and not _longest_partial_tag_suffix(buffer):
            yield buffer

    def generate(self, prompt: str) -> str:
        full_prompt = self._build_prompt(prompt)
        out = self.model.create_completion(**self._completion_kwargs(full_prompt, False))
        return out["choices"][0]["text"]

    # --- UI ---
    def _print_response(self, text: str) -> None:
        # Bersihkan sisa tag thinking jika mode non-stream
        if not self.config["reasoning"]:
            import re
            # Hapus semua blok <think>...</think> yang lengkap (non-greedy, DOTALL agar newline di dalam ikut)
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
            # Buang sisa <think> tanpa pasangan (unclosed) berikut isinya
            if "<think>" in text:
                text = text[: text.index("<think>")]
        console.print(
            Panel(
                Text(text.strip(), style="green"),
                title="[bold green]Model[/bold green]",
                border_style="green",
            )
        )

    def _respond(self, user_input: str) -> None:
        if self.model is None:
            console.print("[red]Model belum dimuat. Gunakan /settings -> change_model.[/red]")
            return
        try:
            if self.config["stream"]:
                response_text = ""
                # leading_done: hanya strip whitespace di awal SATU KALI (iterasi pertama
                # yang punya karakter non-whitespace). Setelah itu, akumulasi ditampilkan
                # mentah agar newline/indent di tengah tidak hilang.
                leading_done = False
                with Live(refresh_per_second=15, screen=False) as live:
                    panel = Panel(Text("..."), title="[bold green]Model[/bold green]", border_style="green")
                    for token in self.stream_generate(user_input):
                        response_text += token
                        if not leading_done:
                            stripped = response_text.lstrip()
                            if stripped:
                                leading_done = True
                                response_text = stripped
                        panel.renderable = Text(response_text, style="green")
                        live.update(panel)
                        # Cek jika user menekan Enter untuk stop
                        if check_stop():
                            console.print("\n[yellow]Generasi dihentikan oleh pengguna.[/yellow]")
                            break
            else:
                self._print_response(self.generate(user_input))
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if Confirm.ask("Reload model?", default=True):
                if self.load_model():
                    console.print("[green]Model reload berhasil.[/green]")

    def show_settings(self) -> None:
        while True:
            # Bersihkan layar agar tabel & menu tidak numpuk dari iterasi sebelumnya
            console.clear()
            self._render_settings_table()

            console.print("[bold cyan]Menu:[/bold cyan]")
            for i, spec in enumerate(PARAM_SPECS, start=1):
                console.print(f"{i}. {spec.key}" + (" (reload)" if spec.needs_reload else ""))
            stream_idx = len(PARAM_SPECS) + 1
            reason_idx = len(PARAM_SPECS) + 2
            sys_idx = len(PARAM_SPECS) + 3
            fmt_idx = len(PARAM_SPECS) + 4
            model_idx = len(PARAM_SPECS) + 5
            console.print(f"{stream_idx}. stream (toggle)")
            console.print(f"{reason_idx}. reasoning (toggle on/off)")
            console.print(f"{sys_idx}. system_prompt")
            console.print(f"{fmt_idx}. prompt_format (reload)")
            console.print(f"{model_idx}. change_model (ganti path/file .gguf)")
            console.print("0. Kembali")

            choice = Prompt.ask("Pilih opsi", choices=[str(i) for i in range(model_idx + 1)], default="0")

            if choice == "0":
                break

            idx = int(choice) - 1
            if 0 <= idx < len(PARAM_SPECS):
                spec = PARAM_SPECS[idx]
                if spec.ask_and_update(self.config) and spec.needs_reload:
                    if Confirm.ask("Reload model sekarang?", default=True):
                        if not self.load_model():
                            console.print("[red]Gagal reload.[/red]")
            elif choice == str(stream_idx):
                self.config["stream"] = not self.config["stream"]
                status = "Aktif" if self.config["stream"] else "Nonaktif"
                console.print(f"[green]Streaming sekarang {status}.[/green]")
            elif choice == str(reason_idx):
                self.config["reasoning"] = not self.config["reasoning"]
                status = "Aktif" if self.config["reasoning"] else "Nonaktif"
                console.print(f"[green]Reasoning/Thinking sekarang {status}.[/green]")
            elif choice == str(sys_idx):
                new = Prompt.ask("System prompt (kepribadian)", default=self.config["system_prompt"])
                self.config["system_prompt"] = new
                console.print("[green]✓ Diperbarui.[/green]")
            elif choice == str(fmt_idx):
                fmt = Prompt.ask(
                    "Format prompt",
                    choices=list(PROMPT_FORMATTERS.keys()),
                    default=self.config["prompt_format"],
                )
                self.config["prompt_format"] = fmt
                console.print("[green]Diperbarui. Reload diperlukan.[/green]")
                if Confirm.ask("Reload model sekarang?", default=True):
                    if not self.load_model():
                        console.print("[red]Gagal reload.[/red]")
            elif choice == str(model_idx):
                self.change_model()

    def _render_settings_table(self) -> None:
        table = Table(title="[bold yellow]Pengaturan Saat Ini[/bold yellow]", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Nilai", style="green")
        # Tampilkan path model aktif
        table.add_row("active_model", os.path.basename(self.model_path))
        for key, val in self.config.items():
            if key in ("stream", "reasoning"):
                val = "Aktif" if val else "Nonaktif"
            table.add_row(key, str(val))
        console.print(table)

    # --- chat loop ---
    def chat_loop(self) -> None:
        console.print(
            Panel.fit(
                f"[bold yellow]🤖 Model Chat (CPU) - Format: {self.config['prompt_format']}[/bold yellow]\n"
                "Ketik pesan atau perintah:\n"
                "  [cyan]/settings[/cyan]  : ubah pengaturan\n"
                "  [cyan]/stream[/cyan]    : toggle streaming\n"
                "  [cyan]/rea[/cyan]       : toggle reasoning/thinking\n"
                "  [cyan]/help[/cyan]      : bantuan\n"
                "  [cyan]/exit[/cyan]      : keluar\n"
                "  [dim]Tekan ENTER saat model membalas untuk menghentikan generasi.[/dim]",
                border_style="blue",
            )
        )

        while self.running:
            try:
                user_input = Prompt.ask("\n[bold blue]Anda[/bold blue]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[red]Keluar.[/red]")
                break

            if not user_input.strip():
                continue

            if user_input.startswith("/"):
                cmd = user_input.lower().strip()
                if cmd in ("/exit", "/quit"):
                    self.running = False
                    break
                if cmd == "/settings":
                    self.show_settings()
                    continue
                if cmd == "/stream":
                    self.config["stream"] = not self.config["stream"]
                    status = "on" if self.config["stream"] else "off"
                    console.print(f"[green]Streaming sekarang {status}.[/green]")
                    continue
                if cmd in ("/rea", "/reason", "/reasoning"):
                    self.config["reasoning"] = not self.config["reasoning"]
                    status = "on" if self.config["reasoning"] else "off"
                    console.print(f"[green]Reasoning sekarang {status}.[/green]")
                    continue
                if cmd == "/help":
                    console.print(
                        "[cyan]/settings[/cyan] - ubah parameter\n"
                        "[cyan]/stream[/cyan]   - toggle streaming\n"
                        "[cyan]/rea[/cyan]      - toggle reasoning/thinking\n"
                        "[cyan]/exit[/cyan]     - keluar"
                    )
                    continue
                console.print("[red]Perintah tidak dikenal. Ketik /help.[/red]")
                continue

            self._respond(user_input)

        self._cleanup_model()


# ---------- Main ----------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chat interaktif dengan model GGUF di CPU - multi-format"
    )
    parser.add_argument("--model", "-m", help="Path ke file/direktori .gguf")
    parser.add_argument(
        "--format", "-f",
        choices=list(PROMPT_FORMATTERS.keys()) + ["auto"],
        default="auto",
        help="Format prompt (auto = deteksi dari nama file)",
    )
    parser.add_argument(
        "-rea", "--reasoning",
        choices=["on", "off"],
        default="on",
        help="Aktifkan atau matikan reasoning/thinking (on/off)",
    )
    args = parser.parse_args()

    raw_path = args.model or Prompt.ask("[bold]Masukkan path file atau direktori .gguf[/bold]")
    model_path = resolve_model_path(raw_path)
    if not model_path:
        console.print("[red]Gagal mendapatkan file model. Keluar.[/red]")
        sys.exit(1)

    app = ChatApp(model_path, args.format, reasoning=(args.reasoning == "on"))
    if not app.load_model():
        console.print("[red]Gagal memuat model. Keluar.[/red]")
        sys.exit(1)

    console.print("[bold]Selamat datang![/bold] Ketik [cyan]/settings[/cyan] untuk mengatur parameter.")
    if Confirm.ask("Ingin mengatur parameter sekarang?", default=False):
        app.show_settings()

    try:
        app.chat_loop()
    except KeyboardInterrupt:
        console.print("\n[red]Dihentikan.[/red]")
    finally:
        console.print("[bold green]Sampai jumpa![/bold green]")


if __name__ == "__main__":
    main()
