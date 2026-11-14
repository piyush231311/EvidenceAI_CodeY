import urllib.request
import urllib.error
import uuid

boundary = "----Boundary" + uuid.uuid4().hex
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="files"; filename="malicious.exe"\r\n'
    f"Content-Type: application/x-msdownload\r\n\r\n"
    f"fake-executable-bytes\r\n"
    f"--{boundary}--\r\n"
).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/cases/test-val-case/evidence",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST"
)

try:
    urllib.request.urlopen(req)
    print("FAILED: Did not reject invalid file!")
except urllib.error.HTTPError as e:
    print(f"PASSED: Correctly rejected invalid file with HTTP {e.code}: {e.read().decode('utf-8')}")
