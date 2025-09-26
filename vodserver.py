import socket, sys
import datetime
import os
import mimetypes
import threading

BUFSIZE = 1024
LARGEST_CONTENT_SIZE = 5242880

class Vod_Server():
    def __init__(self, port_id):
        # create an HTTP port to listen to
        self.http_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.http_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.http_socket.bind(("", port_id))
        self.http_socket.listen(10000)
        self.remain_threads = True

        # load all contents in the buffer
        self.dir = os.path.join(os.getcwd(), 'content')
        self.load_contents(self.dir)
        self.threads = []

        # listen to the http socket

        self.listen()
        for thread in self.threads:
            thread.join()
        pass

    def load_contents(self, dir):
        #Create a list of files and stuff that you have
        contents = []
        confidential = []

        for root, _, files in os.walk(dir):
            curr_root = os.path.relpath(root, dir)
            conf = 'confidential' in curr_root.split(os.sep)
            for file in files:
                path = os.path.normpath(os.path.join(curr_root, file))
                path = path.replace('\\', '/')
                if conf:
                    confidential.append(path)
                else:
                    contents.append(path)

        self.contents = contents
        self.confidential = confidential
        #print(self.contents)
        #print(self.confidential)
        return
    

    def listen(self):
        while self.remain_threads:
            connection_socket, client_address = self.http_socket.accept()
            print(f"Receiving connection from: {client_address}")
            #msg_string = connection_socket.recv(BUFSIZE).decode()
            #parsed_req = self.parse_request(msg_string)
            print("STARTING NEW THREAD")
                
            req_thread = threading.Thread(target=self.response, args = (None, connection_socket))
            self.threads.append(req_thread)
            req_thread.start()
        
    
    def parse_request(self, request):
        req_lines = request.split("\r\n")
        if req_lines[0]:
            req_line = req_lines[0].split()
        else:
            return

        method, file, ver = req_line
        commands = self.eval_commands(req_lines)

        return {
            'method' : method,
            'file': file.lstrip('/'),
            'ver': ver,
            'commands': commands
        }

    def eval_commands(self, commands):
        command_dict = {}
        for item in commands[1:]:
            item = item.rstrip()
            if item and ':' in item:
                splitted_item = item.split(":")
                command_dict[splitted_item[0]] = splitted_item[1].strip()
        return command_dict
    
    def response(self, request, connection_socket):
        try:
            msg_string = connection_socket.recv(BUFSIZE).decode()
            if not msg_string:
                return
            request = self.parse_request(msg_string)
            
            #while True:
            if request['method'] != 'GET':
                return
    
            req_file = request['file']
            req_ver = request['ver']
            req_commands = request['commands']
            connection = req_commands.get('Connection')
            close = True if (connection == 'close') else False
            print(f"requested: {req_file}\r\n")
            
        
            if req_file in self.confidential: # under /confidential/
                self.generate_response_403(req_ver, connection_socket)
                close = True
            elif req_file not in self.contents:
                self.generate_response_404(req_ver, connection_socket)
                close = True
            elif req_file in self.contents:
                # GET - ch
                file_type, _ = mimetypes.guess_type(req_file)
                if not file_type:
                    file_type = 'application/octet-stream'

                # check size of file requested
                file_path = os.path.join(self.dir, req_file)
                total_len = os.path.getsize(file_path)
                

                if 'Range' in req_commands or total_len > LARGEST_CONTENT_SIZE: #if req has range header field
                    self.generate_response_206(req_ver, req_file, file_type, req_commands, connection_socket)
                else: 
                    self.generate_response_200(req_ver, req_file, file_type, connection_socket)

                
                # if close:
                #     break
                # try:
                #     msg_string = connection_socket.recv(BUFSIZE).decode()
                #     if not msg_string:
                #         break
                #     request = self.parse_request(msg_string)
                # except Exception:
                #     break  
        except Exception:
            return
        #finally:
        #    connection_socket.close()
        return
    

    def header(self, httpver, status, content_len, content_type, last_mod, range, connection, accept_range):
        # status = HTTP ver SP Status-code SP reason CRLF
        date = datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

        header = (f"{httpver} {status}\r\n"
                    f"Date: {date}\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {content_len}\r\n"
        )
        if last_mod:
            header += f"Last-Modified: {last_mod}\r\n"
        if accept_range:
            header += f"Accept-Ranges: {accept_range}\r\n"
        if connection:
            header += f"Connection: {connection}\r\n"
        if range:
           header += f'Content-Range: bytes {range}\r\n'

        header += '\r\n'
        return header

    #not found
    def generate_response_404(self, http_version, connection_socket):
        #Generate Response and Send
        try:
            with open('404_not_found.html', 'rb') as f:
                body = f.read()
        except FileNotFoundError:
            body =  b"<html><body> 404 Not Found </body></html>"
        header = self.header(http_version, 
                            '404 Not Found', 
                            len(body), 
                            "text/html", 
                            last_mod=None, 
                            range=None, 
                            connection = 'close', 
                            accept_range=None
                        )
        print(header)
        response = header.encode() + body
        connection_socket.sendall(response)
        return response

    # forbidden
    def generate_response_403(self, http_version, connection_socket):
        #Generate Response and Send
        body = b''
        header = self.header(http_version, 
                            '403 Forbidden', 
                            len(body), 
                            "text/html", 
                            last_mod=None, 
                            range=None, 
                            connection = 'close', 
                            accept_range=None
                        )
        print(header)
        response = header.encode() + body
        connection_socket.sendall(response)
        return response
    
    # success
    def generate_response_200(self, http_version, file_idx, file_type, connection_socket):
        #Generate Response and Send
        file_path = os.path.join(self.dir, file_idx)
        lastMod = os.path.getmtime(file_path)
        lastMod = datetime.datetime.fromtimestamp(lastMod,datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        try:
            with open(file_path, 'rb') as f:
                body = f.read()
        except(FileNotFoundError):
            self.generate_response_404(http_version, connection_socket)
            return

        header = self.header(http_version, 
                            '200 OK', 
                            len(body), 
                            file_type, 
                            last_mod=lastMod, 
                            range=None, 
                            connection = 'Keep-Alive', 
                            accept_range='bytes'
                        )
        print(header)
        response = header.encode() + body
        connection_socket.sendall(response)
        return response

    # partial contenet
    def generate_response_206(self, http_version, file_idx, file_type, command_parameters, connection_socket):
        #Generate Response and Send
        file_path = os.path.join(self.dir, file_idx)
        lastMod = os.path.getmtime(file_path)
        lastMod = datetime.datetime.fromtimestamp(lastMod,datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
      
        total_len = os.path.getsize(file_path)
        if 'Range' in command_parameters:
            range = command_parameters['Range']
            print(f'Requested range: {range}')
            range = command_parameters['Range'].split("bytes=")[1].split('-')
            start = int(range[0]) if range[0] else 0
            req_end = int(range[1]) if range[1] != '' else start + LARGEST_CONTENT_SIZE - 1
        else:
            start = 0
            req_end = LARGEST_CONTENT_SIZE - 1

        end = min(req_end, start + LARGEST_CONTENT_SIZE - 1, total_len - 1)
        read_len = end - start + 1
        
        #connection = 'close' if end == total_len - 1 else 'Keep-Alive'
        connection = 'close' if command_parameters.get('Connection') == 'close' else 'Keep-Alive'
        with open(file_path, 'rb') as f:
            f.seek(start)
            body = f.read(read_len)
            header = self.header(http_version, 
                                '206 Partial Content', 
                                read_len, 
                                file_type, 
                                last_mod=lastMod, 
                                range=f"{start}-{end}/{total_len}", 
                                connection = connection, 
                                accept_range='bytes'
                            )
            print(header)
            response = header.encode() + body
            connection_socket.sendall(response)
        return response


if __name__ == "__main__":
    Vod_Server(int(sys.argv[1]))