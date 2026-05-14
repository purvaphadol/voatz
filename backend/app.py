# from app import create_app

# app = create_app()

# if __name__ == '__main__':
#     # Configure for better concurrent request handling
#     app.run(
#         port=4000,
#         debug=True,
#         host='192.168.10.166',
#         threaded=True,  # Enable threading for concurrent requests
#         processes=1     # Use single process with multiple threads
#     )
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(
        port=4000,
        debug=True,
        host='0.0.0.0',
        threaded=True,
        processes=1
    )