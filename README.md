# zhenpai

![Lint Python](https://github.com/gweng88/zhenpai/workflows/Lint%20Python/badge.svg)
![Deploy](https://github.com/gweng88/zhenpai/workflows/Deploy/badge.svg)
![Python](https://img.shields.io/badge/python-v3.7-blue)  

## Overview
Community discord bot for people who #pretend-to-learn-to-code. 
`zhenpai` currently has the following features/cogs:
* tagging - tag any image with a keyword. Any Discord message containing
the keyword will prompt the bot to respond with the image in an embed.
* twitcasting - subscribe to any [Twitcasting](https://twitcasting.tv/) user
and receive notifications when they start or stop a livestream.

Look at [Setup and Installation](#Setup-and-Installation) for steps on
how to self-host your own bot for development and use in your servers.


## Contributing
Our contributing workflow is as follows. This will setup a copy of the repository on your
Github and push contributions without directly affecting the main repository.

1. Fork a copy of the repository to your own Github by clicking on the top-right Fork button. 
2. Clone the forked copy to your computer.
3. Add a new Git remote pointing to the main repository with `git remote add upstream https://github.com/gweng88/zhenpai.git`.
When you enter `git remote -v`, you should see two remotes, `origin` pointing to your forked repository
and `upstream` pointing to the main repository. The output should look similar to below.
    ```
    origin	https://github.com/<your-github-username>/zhenpai.git (fetch)
    origin	https://github.com/<your-github-username>/zhenpai.git (push)
    upstream	https://github.com/gweng88/zhenpai.git (fetch)
    upstream	https://github.com/gweng88/zhenpai.git (push)
    ```

Whenever you want to create changes and submit them for review and merge, do the following workflow.

1. Pull from upstream to update your local `master` branch: `git checkout main && git pull upstream`.
You should never be directly committing to the `master` branch.
2. Create a new dev branch with `git checkout -b <name-of-dev-branch>`.
3. Make your changes.
4. Push the changes to your forked repository by entering `git push origin <name-of-dev-branch>`.
You should be able to see your changes on Github now.
Run this command every time you want to keep adding changes to your branch after your first push.
5. Make a pull request once you are satisfied with your changes and detail what you are adding/fixing.
You can keep adding changes with `git push origin`, and your pull request will automatically be updated.
6. A contributor will look over the pull request, leave feedback, and merge the commit back into `master`
of the main repository.

## Setup and Installation

There are two ways of running the bot, on a local computer with a Python (>=3.7)
installation (recommended for development) or inside a Docker container (recommended for
self-hosting the bot).

### Running the bot on a computer

#### Prerequisites
* Install Python 3.7 or newer.
* Install Git.
* Create a Discord application and retrieve its bot token [here](https://discord.com/developers/applications).

#### Steps
1. Clone the repository.
2. Open a terminal and change the working directory to the repository.
3. (Optional) Set up a virtual environment in the repository.
4. Install required Python packages in `requirements.txt` by entering `pip install -r requirements.txt`
into the terminal.
5. Create a `config.py` at the top-level directory of the repository with the contents
of `config.example`. Replace the contents of `YOUR_TOKEN` with your bot token.
6. **[Important]** Configure what cogs you want the bot to have by editing the `extensions` list in `bot.py`.
 You can do this to avoid setting up cogs that you don't care about. An example `extensions` list
 including the Tagging cog only looks like the following. Each cog should be prefixed
 by `cog.` because they are placed in the `cogs` directory.
    ```python
    extensions = [
        'cogs.tagging'
    ]
    ```
7. Run the bot by entering `python bot.py` in the terminal. The bot will then go online in
the servers it has been installed to. Close the terminal or `Ctrl+C` to make the bot go offline.

### Running the bot in Docker

#### Prerequisites
* Install Docker.
* Install Git.
* Create a Discord application and retrieve its bot token [here](https://discord.com/developers/applications).

#### Steps
1. Clone the repository.
2. Open a terminal and change the working directory to the repository.
3. Run `docker build . -tag <docker-image-name>` to build the Docker image. Replace `<docker-image-name>`
with what you want to name your image.
4. Run `docker run -it -d -p 80:8080 --restart=always --name=<docker-container-name>
 -v <data-directory>:/opt/app/data <docker-image-name>`.
Replace `<docker-container-name>` with what you want to name your docker container.
Replace `<data-directory>` with a path to the directory where the bot will store persistent
data, such as databases, images, and logs.
Replace `<docker-image-name>` with the image name you created in step 3.
5. Run `docker stop <docker-container-name>` to stop the bot and make it go offline.
Replace `<docker-container-name>` with the name of the Docker container you created in step 4. 

### Installing Your Bot to a Discord Server
Discord.py's guide to creating and installing a bot to a Discord server
is located [here](https://discordpy.readthedocs.io/en/latest/discord.html).
