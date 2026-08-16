import os
import sys
import signal
import readline
import logging
from pathlib import Path

from dotenv import load_dotenv

from konfigurasi import konfigurasi
from llm.loader import LLMLoader
from llm.inference import InferenceEngine
from agen.agen import AgentAI

def main():
    # 1. Konfigurasi logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)

    # 1b. Daftarkan signal handler
    def cleanup(signum=None, frame=None):                                # Mendefinisikan fungsi handler untuk sinyal.
        print("\n\n🔄 Menjalankan cleanup...")                           # Memberi tahu user cleanup dijalankan.
        logger.info("Sinyal diterima, menjalankan cleanup...")          # Mencatat ke log.
        try:                                                             # Blok try untuk menangkap error saat cleanup.
            if loader.is_loaded:                                         # Jika loader sedang memuat model.
                loader.unload()                                          # Panggil unload untuk membongkar model.
                logger.info("Model berhasil dibongkar.")                # Konfirmasi ke log.
        except Exception as e:                                           # Tangkap exception.
            logger.error(f"Error saat cleanup: {e}")                    # Catat error.
        sys.exit(0)                                                      # Keluar program dengan kode sukses.

    signal.signal(signal.SIGINT, cleanup)                               # Handler untuk Ctrl+C.
    signal.signal(signal.SIGTERM, cleanup)                              # Handler untuk terminasi dari OS.
    logger.info("Signal handler terdaftar.")                            # Log konfirmasi.

    from types import SimpleNamespace                                  # Mengimpor SimpleNamespace untuk membuat objek state.
    args = SimpleNamespace(stream=False)                              # Membuat objek args dengan atribut stream=False sebagai default.

    # 1c. Setup readline history (menyimpan riwayat perintah antar sesi)
    # 1. Tentukan file history
    histfile = os.path.expanduser("~/.ai_assistant_history")             # Path file history di home user.
    try:                                                                 # Blok try untuk membaca history jika ada.
        readline.read_history_file(histfile)                             # Muat history dari file.
        logger.debug(f"Readline history dimuat dari {histfile}")        # Log (level DEBUG).
    except FileNotFoundError:                                            # Jika file belum ada.
        pass                                                             # Abaikan, tidak ada history sebelumnya.

    # 2. Daftar perintah yang tersedia (untuk autocomplete)
    commands = [                                                      # List perintah yang dikenali.
        '/help', '/reset', '/planner', '/stats', '/clear',
        '/stream', '/verbose', '/model', 'exit', 'quit'
    ]

    class Completer:                                                # Kelas completer untuk autocomplete.
        def __init__(self, options):                                # Constructor menerima daftar opsi.
            self.options = sorted(options)                          # Simpan opsi yang sudah diurutkan.
        def complete(self, text, state):                            # Method complete dipanggil readline.
            matches = [cmd for cmd in self.options if cmd.startswith(text)]  # Cari yang cocok dengan teks.
            try:
                return matches[state]                               # Kembalikan opsi sesuai state index.
            except IndexError:
                return None

    # Pasang completer
    completer = Completer(commands)                                 # Buat instance completer.
    readline.set_completer(completer.complete)                     # Pasang completer ke readline.
    readline.set_completer_delims(' \t\n;')                        # Karakter pemisah (spasi, tab, newline, ;).
    readline.parse_and_bind("tab: complete")                       # Bind tombol Tab ke fungsi complete.

    # Simpan history saat keluar (pakai atexit)
    import atexit                                                       # Import atexit untuk daftar callback keluar.
    atexit.register(readline.write_history_file, histfile)              # Saat program keluar, simpan history ke file.
    logger.debug("Readline history diaktifkan.")                        # Log konfirmasi.

    # 2. Ambil instance konfigurasi (sudah singleton)
    config = konfigurasi            # Mengambil instance singleton konfigurasi dari modul konfigurasi.py. Instance ini sudah berisi semua nilai dari .env dan default.
    logger.info("Konfigurasi berhasil dimuat.")

    # 2a. Scan model yang tersedia
    models_dir = config.MODELS_DIR                                      # Mengambil path folder models dari konfigurasi.
    model_files = sorted(models_dir.glob("*.gguf"))                    # Mencari semua file .gguf di folder models, diurutkan.
    available_models = [str(f.name) for f in model_files]              # Mengambil hanya nama file (tanpa path).
    current_model_name = Path(config.MODEL_PATH).name                  # Ambil nama model saat ini.

    if not available_models:                                            # Jika tidak ada file .gguf ditemukan.
        logger.warning("Tidak ada model .gguf ditemukan di folder models.")  # Peringatan ke log.
        available_models = []                                           # List kosong.

    current_model_name = Path(config.MODEL_PATH).name                  # Ambil nama file dari MODEL_PATH saat ini.

    logger.info(f"Ditemukan {len(available_models)} model: {', '.join(available_models)}")  # Log daftar model.
    logger.info(f"Model saat ini: {current_model_name}")               # Log model yang sedang digunakan.

    # 3. Inisialisasi LLM Loader
    loader = LLMLoader(                                          # Membuat instance LLMLoader dengan parameter dari config. Loader ini hanya menyiapkan path dan validasi, belum memuat model ke memory.
        model_path=config.MODEL_PATH,              # Path ke file model GGUF (dari .env).
        n_ctx=config.N_CTX,                                     # Panjang konteks (jumlah token input).
        n_gpu_layers=config.N_GPU_LAYERS,       # Jumlah layer yang dipindahkan ke GPU (0 = semua di CPU).
        n_threads=config.N_THREADS,                    # Jumlah thread CPU (0 = auto).
        verbose=config.AGENT_VERBOSE               # Mode verbose untuk logging (true/false dari .env).
    )
    logger.debug("LLMLoader berhasil diinisialisasi.")

    # 4. Muat model
    logger.info(f"Memuat model dari: {config.MODEL_PATH}")
    model = loader.load()
    logger.info("Model berhasil dimuat.")

    # 5. Inisialisasi Inference Engine
    logger.info("Menginisialisasi InferenceEngine...")
    inference = InferenceEngine(                                         # Membuat instance InferenceEngine untuk melakukan inferensi dengan model yang sudah dimuat.
        loader=loader,                                                   # Instance LLMLoader yang sudah berisi model yang dimuat.
        max_tokens=config.MAX_TOKENS,                                    # Maksimal token output yang dihasilkan (dari .env).
        temperature=config.TEMPERATURE,                                  # Kreativitas respons (0-1, makin tinggi makin kreatif).
        top_p=config.TOP_P,                                              # Nucleus sampling (0-1), membatasi token berdasarkan probabilitas kumulatif.
        top_k=config.TOP_K,                                              # Top-K sampling, hanya mempertimbangkan K token teratas.
        repeat_penalty=config.REPEAT_PENALTY,                            # Penalti pengulangan kata (semakin tinggi >1 semakin mencegah repetisi).
        stream=False,                                                    # Mode streaming default (False = batch, bisa diubah via CLI nanti).
        verbose=config.AGENT_VERBOSE                                     # Mode verbose untuk logging (true/false dari .env).
    )
    logger.info("InferenceEngine berhasil diinisialisasi.")

    # 6. Inisialisasi AgentAI
    logger.info("Menginisialisasi AgentAI.")
    agent = AgentAI(                                                      # Membuat instance AgentAI sebagai koordinator utama.
        llm=inference,                                                    # Instance InferenceEngine untuk generate response.
        verbose=config.AGENT_VERBOSE                                      # Mode verbose untuk logging (true/false dari .env).
    )
    logger.info("AgentAI berhasil diinisialisasi.")

    # 6a. Fungsi reload model (di dalam main)
    def reload_model(nama_model: str) -> bool:                           # Mendefinisikan fungsi reload_model dengan parameter nama_model (string) dan mengembalikan boolean (True jika berhasil).
        """Reload model baru dan update agent.llm"""                     # Docstring: menjelaskan tujuan fungsi.
        nonlocal loader, inference, current_model_name                   # Agar bisa mengubah variabel di outer scope (main).

        logger.info(f"Memulai reload ke model: {nama_model}")           # Mencatat bahwa reload dimulai.

        # 1. Cari path lengkap model
        model_path = config.MODELS_DIR / nama_model                     # Membuat path lengkap dengan menggabungkan folder models dan nama model.
        if not model_path.exists():                                      # Cek apakah file model benar-benar ada.
            logger.error(f"File model tidak ditemukan: {model_path}")   # Catat error ke log.
            print(f"❌ File model tidak ditemukan: {nama_model}")       # Tampilkan pesan error ke user.
            return False                                                # Kembalikan False karena gagal.

        # 2. Unload model lama jika ada
        if loader.is_loaded:                                             # Cek apakah loader saat ini sedang memuat model.
            logger.info("Membongkar model lama...")                     # Catat ke log.
            loader.unload()                                              # Panggil unload() untuk membebaskan memory.
            print("⏳ Membongkar model lama...")                        # Tampilkan ke user.

        # 3. Buat loader baru dengan path model baru
        try:                                                             # Mulai blok try untuk menangkap error saat membuat loader.
            new_loader = LLMLoader(                                      # Buat instance LLMLoader baru.
                model_path=str(model_path),                              # Path ke file model (dikonversi ke string).
                n_ctx=config.N_CTX,                                      # Panjang konteks dari konfigurasi.
                n_gpu_layers=config.N_GPU_LAYERS,                       # Jumlah layer GPU dari konfigurasi.
                n_threads=config.N_THREADS,                             # Jumlah thread CPU dari konfigurasi.
                verbose=config.AGENT_VERBOSE                            # Mode verbose dari konfigurasi.
            )
            logger.info("Loader baru berhasil dibuat.")                 # Catat sukses.
        except Exception as e:                                           # Tangkap exception apapun.
            logger.error(f"Gagal membuat loader: {e}")                  # Catat error.
            print(f"❌ Gagal membuat loader: {e}")                      # Tampilkan ke user.
            return False                                                # Kembalikan False.

        # 4. Muat model baru
        try:                                                             # Mulai blok try untuk memuat model.
            print(f"⏳ Memuat model {nama_model}...")                   # Tampilkan ke user.
            new_model = new_loader.load()                               # Panggil load() untuk memuat model ke memory.
            logger.info("Model baru berhasil dimuat.")                 # Catat sukses.
        except Exception as e:                                           # Tangkap exception.
            logger.error(f"Gagal memuat model: {e}")                    # Catat error.
            print(f"❌ Gagal memuat model: {e}")                        # Tampilkan ke user.
            return False                                                # Kembalikan False.

        # 5. Buat InferenceEngine baru
        try:                                                             # Mulai blok try untuk membuat InferenceEngine.
            new_inference = InferenceEngine(                            # Buat instance InferenceEngine baru.
                loader=new_loader,                                      # Gunakan loader baru yang sudah berisi model.
                max_tokens=config.MAX_TOKENS,                          # Maksimal token output.
                temperature=config.TEMPERATURE,                        # Kreativitas.
                top_p=config.TOP_P,                                    # Nucleus sampling.
                top_k=config.TOP_K,                                    # Top-K sampling.
                repeat_penalty=config.REPEAT_PENALTY,                  # Penalti pengulangan.
                stream=False,                                           # Mode streaming default (akan diatur dari args nanti).
                verbose=config.AGENT_VERBOSE                           # Mode verbose.
            )
            logger.info("InferenceEngine baru berhasil dibuat.")       # Catat sukses.
        except Exception as e:                                           # Tangkap exception.
            logger.error(f"Gagal membuat InferenceEngine: {e}")         # Catat error.
            print(f"❌ Gagal membuat InferenceEngine: {e}")             # Tampilkan ke user.
            return False                                                # Kembalikan False.

        # 6. Update agent.llm dengan inference baru
        agent.llm = new_inference                                       # Ganti atribut llm di agent dengan inference baru.
        logger.info("Agent.llm diperbarui dengan inference baru.")     # Catat ke log.

        # 7. Update variabel global/main
        loader = new_loader                                              # Assign loader baru ke variabel loader di outer scope.
        inference = new_inference                                       # Assign inference baru ke variabel inference di outer scope.
        current_model_name = nama_model                                 # Update nama model aktif.

        # 8. Update planner dengan LLM baru (jika planner menggunakan LLM)
        if agent.perencana and agent.perencana.gunakan_llm:             # Cek apakah planner ada dan menggunakan LLM.
            agent.perencana.siapkan_llm(new_inference)                  # Jika ya, set LLM baru ke planner.

        print(f"✅ Berhasil beralih ke model: {nama_model}")            # Konfirmasi ke user.
        logger.info(f"Reload selesai. Model aktif: {nama_model}")      # Catat ke log.
        return True                                                     # Kembalikan True (sukses).

    # 7. Mulai sesi agent
    session_id = agent.mulai_sesi()                                        # Memulai sesi baru atau melanjutkan sesi yang ada (jika diberikan ID). Mengembalikan ID sesi yang aktif.
    logger.info(f"Sesi dimulai dengan ID: {session_id}")                 # Mencatat ID sesi ke log.
    
    # 8. Tampilkan informasi awal ke user
    print("\n" + "=" * 50)                                                # Garis pemisah untuk tampilan yang rapi.
    print("AI Assistant siap digunakan.")                                 # Pesan sambutan.
    print(f"Session ID: {session_id}")                                    # Menampilkan ID sesi agar user tahu sesi yang sedang aktif.
    print(f"Model: {config.MODEL_PATH}")                                  # Menampilkan path model yang digunakan.
    print(f"Planner aktif: {agent.is_planner_active()}")                  # Mengecek status planner (aktif/tidak) melalui method `is_planner_active()`.
    print("Ketik 'exit' atau 'quit' untuk keluar.")                      # Memberi tahu cara keluar dari program.
    print("=" * 50 + "\n")                                                # Garis pemisah akhir.

    # 9. Loop utama (REPL) dengan perintah khusus
    while True:                                                           # Perulangan tak hingga sampai ada break.
        try:                                                              # Blok try untuk menangkap KeyboardInterrupt (Ctrl+C).
            user_input = input("\n>>> ").strip()                          # Menampilkan prompt '>>> ' dan membaca input user, lalu menghilangkan spasi di awal/akhir.

            if not user_input:                                            # Jika input kosong (hanya spasi/enter).
                continue                                                  # Lewati proses dan tampilkan prompt lagi.

            if user_input.lower() in ['exit', 'quit']:                    # Cek apakah user mengetik 'exit' atau 'quit' (case insensitive).
                logger.info("User mengakhiri sesi.")                      # Mencatat aksi keluar ke log.
                break                                                     # Keluar dari while loop.

            if user_input.startswith('/'):                                # Deteksi perintah khusus (diawali '/').
                parts = user_input.split()                                # Memecah input menjadi list berdasarkan spasi.
                cmd = parts[0].lower()                                    # Mengambil perintah (huruf kecil).
                args_cmd = parts[1:]                                      # Menyimpan argumen tambahan (jika ada).

                if cmd == '/help':                                        # Jika perintah '/help'.
                    print("\n📋 Perintah yang tersedia:")                  # Menampilkan judul bantuan.
                    print("  /help           - Tampilkan bantuan ini")   # Info perintah help.
                    print("  /reset          - Reset sesi (hapus percakapan)")  # Info reset.
                    print("  /planner on/off - Aktifkan/nonaktifkan planner (tool mode)")  # Info planner.
                    print("  /stats          - Tampilkan statistik sesi")  # Info statistik.
                    print("  /clear          - Bersihkan layar (clear screen)")  # Info clear.
                    print("  /stream         - Toggle mode streaming (AKTIF/NONAKTIF)")  # Info stream.
                    print("  /verbose        - Toggle verbose logging (DEBUG/INFO)")  # Info verbose.
                    print("  exit, quit      - Keluar dari program")     # Info keluar.
                    print("  /model          - Tampilkan daftar model dan model aktif")  # Info model.
                    print("  /model switch <nama> - Ganti ke model lain")  # Info switch.
                    continue                                              # Kembali ke awal loop.

                elif cmd == '/reset':                                     # Jika perintah '/reset'.
                    logger.info("Reset sesi diminta oleh user.")         # Catat ke log.
                    agent.reset()                                         # Panggil reset() untuk membersihkan agent.
                    session_id = agent.mulai_sesi()                       # Mulai sesi baru setelah reset.
                    print(f"🔄 Sesi direset. ID sesi baru: {session_id}") # Konfirmasi ke user.
                    continue                                              # Kembali ke awal loop.

                elif cmd == '/planner':                                   # Jika perintah '/planner'.
                    if not args_cmd:                                      # Jika tidak ada argumen (hanya '/planner').
                        print(f"📌 Status planner saat ini: {'AKTIF' if agent.is_planner_active() else 'NONAKTIF'}")  # Tampilkan status.
                        print("   Gunakan: /planner on  atau  /planner off")  # Petunjuk penggunaan.
                    elif args_cmd[0].lower() == 'on':                     # Jika argumen 'on'.
                        agent.toggle_planner(True)                        # Aktifkan planner (mode tool).
                        print("✅ Planner diaktifkan (mode tool)")        # Konfirmasi.
                    elif args_cmd[0].lower() == 'off':                    # Jika argumen 'off'.
                        agent.toggle_planner(False)                       # Nonaktifkan planner (mode chat).
                        print("✅ Planner dinonaktifkan (mode chat)")     # Konfirmasi.
                    else:                                                 # Jika argumen tidak dikenal.
                        print("❌ Argumen tidak dikenal. Gunakan 'on' atau 'off'.")  # Pesan error.
                    continue                                              # Kembali ke awal loop.

                elif cmd == '/stats':                                     # Jika perintah '/stats'.
                    stats = agent.status_agen_terakhir()                  # Ambil statistik dari agent.
                    print("\n📊 Statistik sesi:")                         # Judul statistik.
                    print(f"  Total queries   : {stats.get('total_queries', 0)}")  # Total pertanyaan.
                    print(f"  Tool calls      : {stats.get('total_tool_calls', 0)}")  # Total tool calls.
                    print(f"  Errors          : {stats.get('total_errors', 0)}")  # Total error.
                    success_rate = stats.get('success_rate', 0) * 100    # Hitung success rate dalam persen.
                    print(f"  Success rate    : {success_rate:.1f}%")     # Tampilkan success rate.
                    print(f"  Session ID      : {stats.get('identitas_sesi', 'N/A')}")  # ID sesi.
                    mem_stats = stats.get('memory', {})                   # Ambil statistik memory.
                    print(f"  Messages in DB  : {mem_stats.get('total_messages', 0)}")  # Total pesan di DB.
                    continue                                              # Kembali ke awal loop.

                elif cmd == '/clear':                                     # Jika perintah '/clear'.
                    os.system('cls' if os.name == 'nt' else 'clear')     # Bersihkan layar (cross-platform).
                    print("\n🔄 Layar dibersihkan.")                      # Konfirmasi ke user.
                    continue                                              # Kembali ke awal loop.

                elif cmd == '/stream':                                    # Jika perintah '/stream'.
                    args.stream = not args.stream                          # Toggle nilai stream.
                    status = "AKTIF" if args.stream else "NONAKTIF"        # Tentukan status teks.
                    print(f"🔄 Mode streaming: {status}")                  # Tampilkan status.
                    continue                                              # Kembali ke awal loop.

                elif cmd == '/model':                                     # Jika perintah '/model'.
                    if not available_models:                              # Jika tidak ada model tersedia.
                        print("❌ Tidak ada model .gguf ditemukan di folder models.")  # Pesan error.
                    elif not args_cmd:                                    # Jika tidak ada argumen (hanya '/model').
                        print("\n📦 Model yang tersedia:")                # Judul daftar model.
                        for i, name in enumerate(available_models, 1):   # Loop dengan indeks mulai 1.
                            marker = "👉 " if name == current_model_name else "  "  # Tandai model aktif.
                            print(f"{marker}{i}. {name}")                 # Tampilkan nomor dan nama.
                        print(f"\n🔹 Model saat ini: {current_model_name}")  # Tampilkan model aktif.
                        print("   Gunakan: /model switch <nama_model> untuk berganti")  # Petunjuk.
                    elif args_cmd[0].lower() == 'switch' and len(args_cmd) > 1:  # Jika argumen 'switch' dan ada nama.
                        target = args_cmd[1]                               # Ambil nama model yang diminta.
                        # Cari model yang cocok (case-insensitive, partial match)
                        matched = [m for m in available_models if target.lower() in m.lower()]  # Cari yang mengandung string.
                        if not matched:                                   # Jika tidak ada yang cocok.
                            print(f"❌ Model '{target}' tidak ditemukan.")  # Pesan error.
                        elif len(matched) > 1:                            # Jika lebih dari satu cocok.
                            print(f"❌ Beberapa model cocok: {', '.join(matched)}")  # Tampilkan pilihan.
                            print("   Gunakan nama yang lebih spesifik.")  # Petunjuk.
                        else:                                             # Hanya satu yang cocok.
                            new_model = matched[0]                        # Ambil nama model yang cocok.
                            if new_model == current_model_name:           # Jika sama dengan model aktif.
                                print(f"✅ Model '{new_model}' sudah aktif.")  # Konfirmasi.
                            else:
                                # Panggil fungsi reload
                                if reload_model(new_model):               # Jika reload sukses.
                                    print(f"✅ Sekarang menggunakan model: {new_model}")  # Konfirmasi.
                                else:                                     # Jika gagal.
                                    print(f"❌ Gagal beralih ke model: {new_model}")  # Pesan error.
                    else:                                                 # Jika argumen tidak dikenal.
                        print("❌ Argumen tidak dikenal. Gunakan: /model switch <nama_model>")  # Pesan error.
                    continue                                              # Kembali ke awal loop.

                elif cmd == '/verbose':                                   # Jika perintah '/verbose'.
                    if logger.level == logging.DEBUG:                     # Cek level logging saat ini.
                        logger.setLevel(logging.INFO)                     # Turunkan ke INFO.
                        print("🔇 Verbose: NONAKTIF (INFO)")              # Konfirmasi.
                    else:                                                  # Jika level bukan DEBUG (INFO atau lebih tinggi).
                        logger.setLevel(logging.DEBUG)                    # Naikkan ke DEBUG.
                        print("🔊 Verbose: AKTIF (DEBUG)")                # Konfirmasi.
                    continue                                              # Kembali ke awal loop.

                else:                                                     # Jika perintah tidak dikenal.
                    print(f"❌ Perintah tidak dikenal: {cmd}. Ketik /help untuk daftar.")  # Pesan error.
                    continue                                              # Kembali ke awal loop.

            # --- Proses pertanyaan normal ---
            logger.info(f"Memproses: {user_input[:50]}...")              # Catat pertanyaan ke log (potong 50 karakter).
            result = agent.proses(user_input, stream=args.stream)        # Panggil agent.proses() dengan mode stream sesuai args.stream.

            response = result.get('respon') or result.get('response')    # Ambil respons (prioritas 'respon' lalu 'response').
            if response:                                                  # Jika ada respons.
                print(f"\n🤖 Assistant: {response}")                      # Tampilkan respons.
            else:                                                         # Jika tidak ada respons (error).
                print(f"\n❌ Error: {result.get('error', 'Unknown error')}")  # Tampilkan pesan error.

            if config.AGENT_VERBOSE:                                      # Jika verbose diaktifkan di konfigurasi.
                print(f"   [Tokens: {result.get('tokens', 0)}, Latency: {result.get('total_latency', 0):.2f}s]")  # Tampilkan metadata.

        except KeyboardInterrupt:                                         # Tangkap Ctrl+C.
            print("\n\n👋 Keluar dari program...")                        # Pesan keluar.
            break                                                         # Keluar dari loop.

    # 10. Cleanup setelah loop utama
    logger.info("Memulai proses cleanup...")
    stats = agent.status_agen_terakhir()
    print("\n" + "=" * 50)
    print("STATISTIK AKHIR")
    print(f"  Total queries: {stats.get('total_queries', 0)}")
    print(f"  Total tool calls: {stats.get('total_tool_calls', 0)}")
    print(f"  Total errors: {stats.get('total_errors', 0)}")
    success_rate = stats.get('success_rate', 0) * 100
    print(f"  Success rate: {success_rate:.1f}%")
    print(f"  Session ID: {stats.get('identitas_sesi', 'N/A')}")
    print("=" * 50 + "\n")

    logger.info("Membongkar model dari memory...")
    loader.unload()
    logger.info("Model berhasil dibongkar.")

    agent.reset()
    logger.info("Agent berhasil di-reset.")

    logger.info("Program selesai.")
    print("👋 Sampai jumpa!")


if __name__ == "__main__":
    main()