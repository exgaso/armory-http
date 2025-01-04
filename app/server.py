import http.server
import socketserver
import os
import sys
import threading
import select
import logging
from urllib.parse import urlparse
from tqdm import tqdm
import socket
import re

UPLOAD_DIRECTORY = "./uploads"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

def sanitize_filename(filename):
    """Sanitize the uploaded filename to allow only alphanumeric characters and one dot."""
    # Remove invalid characters (allow only a-z, A-Z, 0-9, and a single dot)
    sanitized = re.sub(r'[^a-zA-Z0-9.]', '_', filename)
    
    # Ensure only one dot is allowed
    if sanitized.count('.') > 1:
        raise ValueError("Filename contains multiple dots.")
    
    return sanitized

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def copyfile(self, source, outputfile):
        """Copy data from source to outputfile with a progress bar."""
        fs = os.fstat(source.fileno())
        total_size = fs.st_size

        with tqdm(total=total_size, unit="B", unit_scale=True, desc=self.path[1:], ncols=100) as progress:
            while True:
                buf = source.read(64 * 1024)
                if not buf:
                    break
                outputfile.write(buf)
                progress.update(len(buf))

    def send_error(self, code, message=None, explain=None):
        self.send_response(code)
        self.end_headers()

    def version_string(self):
        return ""

    def do_GET(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            self.send_error(404)
            return
        super().do_GET()

    def do_POST(self):
        """Handle POST requests for file uploads."""
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/upload":
            content_type = self.headers.get("Content-Type")
            if not content_type or "multipart/form-data" not in content_type:
                self.send_error(400, "Invalid content type")
                return

            boundary = content_type.split("boundary=")[-1]
            if not boundary:
                self.send_error(400, "Missing boundary in content type")
                return

            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self.send_error(400, "Invalid content length")
                return

            # Read POST data (multipart form data)
            post_data = self.rfile.read(content_length).decode("utf-8", errors="ignore")

            # Split by boundary and extract parts
            parts = post_data.split(f"--{boundary}")
            for part in parts:
                if "Content-Disposition: form-data" in part and 'filename="' in part:
                    # Extract filename from the part
                    filename_start = part.find('filename="') + 10
                    filename_end = part.find('"', filename_start)
                    filename = part[filename_start:filename_end]

                    # If no filename found, continue to next part
                    if not filename:
                        continue

                    try:
                        # Sanitize the filename
                        sanitized_filename = sanitize_filename(filename)
                    except ValueError:
                        self.send_error(400, "Invalid filename")
                        return

                    # Extract file content
                    content_start = part.find("\r\n\r\n") + 4
                    content_end = part.rfind("\r\n")
                    file_content = part[content_start:content_end]

                    # Save file
                    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
                    file_path = os.path.join(UPLOAD_DIRECTORY, sanitized_filename)

                    logging.info(f"Starting upload of {sanitized_filename}...")

                    try:
                        with open(file_path, "wb") as f:
                            with tqdm(total=len(file_content), unit="B", unit_scale=True, desc=f"Uploading {sanitized_filename}", ncols=100) as progress:
                                # Writing in chunks and updating progress
                                chunk_size = 1024  # 1 KB per chunk
                                for i in range(0, len(file_content), chunk_size):
                                    chunk = file_content[i:i + chunk_size]
                                    f.write(chunk.encode("utf-8", errors="ignore"))
                                    progress.update(len(chunk))

                        # Log upload
                        logging.info(f"Uploaded: {sanitized_filename} (Size: {len(file_content)} bytes)")

                        # Respond success
                        self.send_response(201)
                        self.end_headers()
                        self.wfile.write(b"File uploaded successfully")
                    except ConnectionResetError:
                        logging.warning(f"Connection reset by peer while uploading {sanitized_filename}")
                        self.send_error(500, "Connection reset by peer")
                    except Exception as e:
                        logging.error(f"Error while uploading {sanitized_filename}: {e}")
                        self.send_error(500, "Internal Server Error")

                    return

            self.send_error(400, "File upload failed")
        else:
            self.send_error(404)

def monitor_keypress(stop_event):
    print("Press 'L' to list the current directory contents.")
    while not stop_event.is_set():
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        if ready:
            key = sys.stdin.read(1).strip()
            if key.upper() == 'L':
                print("\nCurrent Directory Contents:")
                for item in sorted(os.listdir('.')):
                    print(f"  - {item}")

def main():
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            print("Invalid port number. Please specify a number between 1 and 65535.")
            sys.exit(1)
    else:
        port = 80

    stop_event = threading.Event()

    Handler = CustomHTTPRequestHandler
    
    try:
        # Create the ThreadingTCPServer to handle multiple requests concurrently
        with socketserver.ThreadingTCPServer(("", port), Handler) as httpd:
            # Allow the socket to be reused immediately after the server shuts down
            httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            logging.info(f"Serving on port {port}")
            
            # Start the keypress monitoring thread
            keypress_thread = threading.Thread(target=monitor_keypress, args=(stop_event,), daemon=True)
            keypress_thread.start()

            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                logging.info("\nShutting down the server...")
                stop_event.set()  # Stop the keypress thread
                httpd.server_close()
    
    except OSError as e:
        if e.errno == 98:  # Address already in use (error number 98 on Linux)
            print(f"Error: Port {port} is already in use. Please try a different port.")
        else:
            print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
