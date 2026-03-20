import customtkinter as ctk
import os
import subprocess
import re
from datetime import datetime
import imageio_ffmpeg
import threading

class LightweightRecorder(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.ffmpeg_process = None
        self.log_file = None

        self.title("RawRec - Universal Edition")
        self.state('zoomed') 
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.save_folder = os.path.join(os.path.expanduser("~"), "Videos", "RawRec")
        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)
        self.current_file_path = ""

        self.main_frame = ctk.CTkFrame(self, corner_radius=15, width=450)
        self.main_frame.pack(pady=50, padx=50, expand=True)

        self.label = ctk.CTkLabel(self.main_frame, text="Ready to Record", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.pack(pady=(30, 20), padx=40)

        self.available_mics = self.get_windows_audio_devices()

        self.audio_switch = ctk.CTkSwitch(self.main_frame, text="Capture Desktop Audio (Requires Stereo Mix)")
        self.audio_switch.pack(pady=10, padx=40, anchor="w")
        self.audio_switch.select()

        mic_text = "Capture Microphone" if self.available_mics else "Microphone Not Found (Disabled)"
        self.mic_switch = ctk.CTkSwitch(self.main_frame, text=mic_text)
        self.mic_switch.pack(pady=10, padx=40, anchor="w")
        
        if self.available_mics:
            self.mic_switch.select()
            self.selected_mic = self.available_mics[0] 
        else:
            self.mic_switch.configure(state="disabled")
            self.selected_mic = None

        self.fps_label = ctk.CTkLabel(self.main_frame, text="Framerate:")
        self.fps_label.pack(pady=(20, 0), padx=40, anchor="w")
        
        self.fps_option = ctk.CTkComboBox(self.main_frame, values=["60", "30"])
        self.fps_option.pack(pady=(5, 20), padx=40, fill="x")

        self.record_btn = ctk.CTkButton(
            self.main_frame, 
            text="START RECORDING", 
            fg_color="#cc0000", 
            hover_color="#ff3333",
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.toggle_recording
        )
        self.record_btn.pack(pady=20, padx=40, fill="x")

        self.status_label = ctk.CTkLabel(
            self.main_frame, 
            text=f"Saves to: {self.save_folder}", 
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray",
            wraplength=350
        )
        self.status_label.pack(pady=(0, 20), padx=40, anchor="w")

        self.is_recording = False

    def get_windows_audio_devices(self):
        cmd = [self.ffmpeg_exe, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy']
        try:
            result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            devices = []
            for line in result.stderr.split('\n'):
                if '(audio)' in line:
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        devices.append(match.group(1))
            return devices
        except Exception:
            return []

    def toggle_recording(self):
        if not self.is_recording:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_file_path = os.path.join(self.save_folder, f"Recording_{timestamp}.mkv")
            
            # Create a log file right next to the video
            log_path = os.path.join(self.save_folder, f"CrashLog_{timestamp}.txt")
            self.log_file = open(log_path, "w")
            
            fps = self.fps_option.get()

            cmd = [
                self.ffmpeg_exe, '-y', 
                '-f', 'gdigrab', '-framerate', fps, '-i', 'desktop'
            ]

            if self.mic_switch.get() == 1 and self.selected_mic:
                cmd.extend(['-f', 'dshow', '-i', f'audio={self.selected_mic}'])

            cmd.extend([
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p',
                self.current_file_path
            ])

            try:
                # Route stderr to our log file so we can see what kills it in the .exe
                self.ffmpeg_process = subprocess.Popen(
                    cmd, 
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.DEVNULL, 
                    stderr=self.log_file, 
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                self.is_recording = True
                self.record_btn.configure(text="STOP RECORDING", fg_color="#228B22", hover_color="#32CD32")
                self.label.configure(text="Recording Live", text_color="#cc0000")
                self.status_label.configure(text=f"Writing to: {self.current_file_path}", text_color="white")
            except Exception:
                self.label.configure(text="Engine Failure!", text_color="#cc0000")

        else:
            self.record_btn.configure(state="disabled", text="SAVING...")
            threading.Thread(target=self.safe_stop_engine).start()

    def safe_stop_engine(self):
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.write(b'q\n')
                self.ffmpeg_process.stdin.flush()
                self.ffmpeg_process.wait(timeout=5) 
            except Exception:
                # If the pipe is broken in the exe, gracefully terminate instead of hard killing
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=3)
        
        if self.log_file:
            self.log_file.close()
            
        self.after(0, self.reset_ui)

    def reset_ui(self):
        self.is_recording = False
        self.record_btn.configure(state="normal", text="START RECORDING", fg_color="#cc0000", hover_color="#ff3333")
        self.label.configure(text="Ready to Record", text_color="white")
        self.status_label.configure(text=f"Saved: {self.current_file_path}", text_color="#32CD32")

if __name__ == "__main__":
    app = LightweightRecorder()
    app.mainloop()
