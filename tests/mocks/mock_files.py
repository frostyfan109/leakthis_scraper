import os

mock_files = [
    {
        "file_name": "file_audio1.mp3",
        "file_data": open(os.path.join(os.path.dirname(__file__), "audio", "audio1.mp3"), "rb")
    },
    {
        "file_name": "file_audio2.mp3",
        "file_data": open(os.path.join(os.path.dirname(__file__), "audio", "audio2.mp3"), "rb")
    }
]

for file in mock_files:
    file["file_length"] = len(file["file_data"].read())
    file["file_data"].seek(0)
