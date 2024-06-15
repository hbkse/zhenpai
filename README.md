# zhenpai

Community discord bot for people who #pretend-to-learn-to-code. [Invite Link](https://discord.com/api/oauth2/authorize?client_id=670839356872982538&permissions=4398046511089&scope=bot)

Currently hosting and deploying to [Railway](https://railway.app/)

## Running locally

Requires at least python 3.8.

Create your own `.env` file based on `.env.example`. You can create a bot and grab the token from the [Discord Developer Portal](https://discord.com/developers/applications)

Create venv: `python -m venv myenv`

Activate venv: `source myenv/bin/activate`

Install packages: `pip install --no-cache-dir -U -r requirements.txt`

Run: `python start.py`.

Deactivate venv: `deactivate`