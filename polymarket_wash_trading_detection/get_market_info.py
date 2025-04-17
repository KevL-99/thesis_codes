import requests
import json
import os


base_url = "https://gamma-api.polymarket.com/markets"
limit = 100
offset = 0
output= os.path.join(os.path.dirname(__file__),"./data/markets.json")

with open(output, "w") as file:
    json.dump([], file)

while True:
    params = {"limit": limit, "offset": offset}
    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code}")
        break

    resp = response.json()
    if resp == []:
        print("Done")
        break

    # append to output file
    with open(output, "r+") as file:
        markets = json.load(file)
        markets.extend(resp)
        file.seek(0)
        json.dump(markets, file)
        file.truncate()

    print(f"Offset: {offset}")
    offset += 100