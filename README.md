#  HTTP Server / Video Streaming Project

This project builds **file server over HTTP** that serves content from a specified content root directory. The server:  
- Generates proper HTTP responses including headers and entity body.  
- Supports video streaming via HTTP range requests, allowing browsers to fetch chunks of files as needed.  

## HTTP Protocol Support
The server implements:  
- **Methods:** GET  
- **Status Codes:**  
  - 200 OK  
  - 206 Partial Content  
  - 403 Forbidden  
  - 404 Not Found  
- **Headers:**  
  - Date (GMT / RFC 1123 format)  
  - Content-Length, Content-Range, Content-Type  
  - Connection: Keep-Alive / close  
  - Accept-Ranges  
  - Last-Modified  

Supported media types based on file extension:  
- Text: `.txt`, `.css`, `.html`  
- Images: `.jpg`, `.jpeg`, `.png`, `.gif`  
- Video: `.mp4`, `.webm`, `.ogg`  
- Scripts: `.js`  
- Binary: others → `application/octet-stream` 

## Content & Access
- Confidential files in `./content/confidential/` are inaccessible (403 Forbidden).  
- File size limit: ≤ 5 MB for regular requests; larger files use partial content streaming.
-* Sample test files are not included.
