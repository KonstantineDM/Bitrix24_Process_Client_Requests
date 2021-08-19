from flask import Flask, request

from query_script import main

app = Flask(__name__)

@app.route("/process_query", methods=["POST"])
def site_request_to_b24():
    query_data = request.get_json()
    main(query_data)
    return query_data


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
