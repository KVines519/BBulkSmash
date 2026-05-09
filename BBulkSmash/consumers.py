from django.conf import settings
import asyncio
import logging
import os, re, signal, psutil
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
import json, socket

logger = logging.getLogger(__name__)

SCREEN_LOG_SUFFIX = '_screen.log'


class SippLogConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        self.stream_task = None
        self.running = False

        query_params = parse_qs(self.scope["query_string"].decode())
        self.xml = query_params.get("xml", [None])[0]
        self.pid = query_params.get("pid", [None])[0]
        self.cport = query_params.get("cp", [None])[0]

        # pid is always required; xml and cport may be "None" for manually-launched SIPp
        if not self.pid or self.pid == "None":
            await self.send(text_data="[ERROR] Missing required PID parameter.")
            await self.close()
            return

        # Treat literal "None" strings as missing
        if self.xml == "None":
            self.xml = None
        if self.cport == "None":
            self.cport = None

        self.running = True
        self.log_dir = str(settings.BASE_DIR / 'logs')

        # stdout log (for final stats after exit) is always in /app/logs/
        if self.xml and not self.xml.startswith("pid"):
            self.stdout_log_path = os.path.join(self.log_dir, f"{self.xml}.xml_{self.pid}.log")
        else:
            self.stdout_log_path = None

        # Screen log path will be discovered after first SIGUSR2
        self.log_file_path = None

        self.stream_task = asyncio.create_task(self.stream_logs())

    async def disconnect(self, close_code):
        self.running = False
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
        # Stop any associated tcpdump capture on disconnect
        try:
            from BBulkSmash.scripts.bbsipp import stop_tcpdump
            stop_tcpdump(int(self.pid))
        except (ValueError, TypeError, Exception):
            pass

    async def stream_logs(self):
        try:
            proc = psutil.Process(int(self.pid))
            log_file_ready = False
            while self.running:
                if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                    try:
                        proc.wait(timeout=2)
                    except psutil.TimeoutExpired:
                        pass
                    # Stop any associated tcpdump capture
                    from BBulkSmash.scripts.bbsipp import stop_tcpdump
                    stop_tcpdump(int(self.pid))
                    # Read the stdout log which has the complete final statistics
                    final_log = None
                    if self.stdout_log_path and os.path.exists(self.stdout_log_path):
                        final_log = self.stdout_log_path
                    elif self.log_file_path and os.path.exists(self.log_file_path):
                        final_log = self.log_file_path
                    if final_log:
                        with open(final_log, 'r') as f:
                            content = f.read(524288)
                        await self.send(text_data=content)
                    await self.send(text_data=f"[NotRunning] SIPp process with pid {self.pid} has exited.")
                    break

                else:
                    try:
                        os.kill(int(self.pid), signal.SIGUSR2)
                    except (ProcessLookupError, PermissionError) as e:
                        await self.send(text_data=f"[ERROR] Cannot send SIGUSR2 to pid {self.pid}: {e}")
                        break
                    await asyncio.sleep(0.4)

                    # Discover the screen log file after SIGUSR2
                    if not log_file_ready:
                        self.log_file_path = self._discover_screen_log()
                        if self.log_file_path and os.path.exists(self.log_file_path):
                            log_file_ready = True
                        else:
                            await asyncio.sleep(1.0)
                            self.log_file_path = self._discover_screen_log()
                            if self.log_file_path and os.path.exists(self.log_file_path):
                                log_file_ready = True
                            else:
                                diag = f"[Waiting] Searching for screen log (pid={self.pid})..."
                                await self.send(text_data=diag)

                    if log_file_ready and self.log_file_path:
                        with open(self.log_file_path, 'r') as f:
                            content = f.read(524288)
                        await self.send(text_data=content)

                    await asyncio.sleep(0.8)

        except psutil.NoSuchProcess:
            from BBulkSmash.scripts.bbsipp import stop_tcpdump
            stop_tcpdump(int(self.pid))
            final_log = None
            if self.stdout_log_path and os.path.exists(self.stdout_log_path):
                final_log = self.stdout_log_path
            elif self.log_file_path and os.path.exists(self.log_file_path):
                final_log = self.log_file_path
            if final_log:
                with open(final_log, 'r') as f:
                    content = f.read(524288)
                await self.send(text_data=content)
            await self.send(text_data=f"[NotRunning] SIPp process with pid {self.pid} has exited.")

        except Exception as e:
            await self.send(text_data=f"[ERROR] Could not read screen log: {str(e)}")

    def _discover_screen_log(self):
        """Find the screen log file for this PID.

        SIPp names screen logs as <scenario>_<pid>_screen.log in its cwd.
        Search the logs directory first, then BASE_DIR (/app), then process cwd.
        """
        pid_str = str(self.pid)
        suffix = '_' + pid_str + SCREEN_LOG_SUFFIX

        # Search logs dir, then BASE_DIR, then process cwd if accessible
        base_dir = str(settings.BASE_DIR)
        search_dirs = [self.log_dir]
        if base_dir != self.log_dir:
            search_dirs.append(base_dir)
        try:
            proc = psutil.Process(int(self.pid))
            proc_cwd = proc.cwd()
            if proc_cwd and proc_cwd not in search_dirs:
                search_dirs.append(proc_cwd)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        for search_dir in search_dirs:
            try:
                for fname in os.listdir(search_dir):
                    if fname.endswith(suffix) and len(fname) > len(suffix):
                        full_path = os.path.join(search_dir, fname)
                        if os.path.isfile(full_path):
                            return full_path
            except OSError:
                pass
        return None

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get("action")

            if action == "send_signal":
                key = data.get("key", "")

                if key == "kill":
                    try:
                        from BBulkSmash.scripts.bbsipp import is_sipp_pid, stop_tcpdump
                        pid_int = int(self.pid)
                        if not is_sipp_pid(pid_int):
                            await self.send(text_data=f"[ERROR] PID {pid_int} is not a known SIPp process")
                        else:
                            process = psutil.Process(pid_int)
                            process.terminate()
                            process.wait(timeout=2)
                            stop_tcpdump(pid_int)
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        pass

                elif key:
                    if not self.cport:
                        await self.send(text_data="[ERROR] No control port -- cannot send keystrokes to manually-launched SIPp")
                        return
                    udp_ip = "127.0.0.1"
                    udp_port = int(self.cport)
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        sock.sendto(key.encode(), (udp_ip, udp_port))
                        sock.close()
                        await self.send(text_data=f"Sent key '{key}' to SIPp on port {udp_port}")
                    except Exception as e:
                        await self.send(text_data=f"[ERROR] Sending UDP: {str(e)}")
                else:
                    await self.send(text_data="[ERROR] No key provided")

            else:
                await self.send(text_data="[ERROR] Unknown action")

        except Exception as e:
            await self.send(text_data=f"[ERROR] {str(e)}")



class SngrepConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that spawns sngrep in a PTY and relays
    bytes bidirectionally so xterm.js can render the full ncurses UI.

    Query params:
      ports  -- comma-separated SIP port list for BPF filter (e.g. "5060,5061")
    """

    async def connect(self):
        await self.accept()
        self.master_fd = None
        self.child_pid = None
        self.read_task = None

        query_params = parse_qs(self.scope["query_string"].decode())

        # Build SIP-only BPF filter from comma-separated port list
        raw_ports = query_params.get("ports", ["5060"])[0]
        port_list = [p.strip() for p in raw_ports.split(",") if p.strip().isdigit()]
        if not port_list:
            port_list = ["5060"]
        sip_bpf = " or ".join(f"port {p}" for p in port_list)

        try:
            import pty as pty_mod
            import subprocess
            import tempfile

            master_fd, slave_fd = pty_mod.openpty()
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"

            # Per-session sngreprc so F2 save dialog defaults to /app/logs/
            logs_dir = str(settings.BASE_DIR / 'logs')
            self._sngreprc_file = tempfile.NamedTemporaryFile(
                mode='w', prefix='sngreprc_', suffix='.conf',
                dir='/tmp', delete=False
            )
            self._sngreprc_file.write(f"set savepath {logs_dir}\n")
            self._sngreprc_file.flush()
            self._sngreprc_file.close()
            env["SNGREPRC"] = self._sngreprc_file.name

            # SIP-only mode: BPF restricts capture to SIP ports
            cmd = ["sngrep", "-d", "any", "", sip_bpf]

            self.proc = subprocess.Popen(
                cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                preexec_fn=os.setsid,
            )
            os.close(slave_fd)
            self.master_fd = master_fd
            self.child_pid = self.proc.pid
            self.read_task = asyncio.create_task(self._read_pty())

        except Exception as e:
            await self.send(text_data=f"\r\n[ERROR] Failed to start sngrep: {e}\r\n")
            await self.close()

    async def disconnect(self, close_code):
        if self.read_task:
            self.read_task.cancel()
            try:
                await self.read_task
            except asyncio.CancelledError:
                pass
        if hasattr(self, 'proc') and self.proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
        if hasattr(self, '_sngreprc_file'):
            try:
                os.unlink(self._sngreprc_file.name)
            except OSError:
                pass

    async def _read_pty(self):
        """Read from the PTY master fd and send bytes to the WebSocket."""
        loop = asyncio.get_event_loop()
        try:
            while True:
                data = await loop.run_in_executor(None, self._blocking_read)
                if not data:
                    break
                await self.send(bytes_data=data)
        except (asyncio.CancelledError, OSError):
            pass

    def _blocking_read(self):
        try:
            return os.read(self.master_fd, 4096)
        except OSError:
            return b""

    async def receive(self, text_data=None, bytes_data=None):
        """Forward keyboard input from xterm.js to the PTY, or handle resize."""
        if text_data:
            try:
                msg = json.loads(text_data)
                if isinstance(msg, dict) and msg.get("type") == "resize":
                    self._resize_pty(msg.get("cols", 80), msg.get("rows", 24))
                    return
            except (json.JSONDecodeError, ValueError):
                pass

        payload = bytes_data if bytes_data else (text_data.encode() if text_data else None)
        if payload and self.master_fd is not None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._blocking_write, payload)

    def _resize_pty(self, cols, rows):
        """Set the PTY window size so ncurses apps redraw correctly."""
        if self.master_fd is None:
            return
        try:
            import struct, fcntl, termios
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            if hasattr(self, 'proc') and self.proc.poll() is None:
                os.kill(self.proc.pid, signal.SIGWINCH)
        except (OSError, Exception):
            pass

    def _blocking_write(self, data):
        try:
            os.write(self.master_fd, data)
        except OSError:
            pass
