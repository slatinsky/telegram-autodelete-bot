# Telegram Autodelete Bot

Python bot to auto-delete messages from a telegram group exactly after specified time in seconds.


## Why?

Shortest auto-delete timer in a telegram group is 1 day. This bot allows you to delete messages after a much shorter time, e.g. 1 minute.


## Prerequisites

- Telegram account with `Add new admin` permission in the group you want to use the bot in (or ask someone with that permission add the bot to the group)
- Always-on server to run the bot on (uptime doen't need to be 100 %, the bot will pickup messages that were sent while the bot was down)


## Limitations

- Telegram bots can't read message history, so the bot will only delete messages that were sent after the bot was added to the group
- Telegram bots can't read messages from other bots (to prevent infinite loop), so the bot will not delete those messages
- The bot saves undeleted message IDs in a sqlite3 database `messages.sqlite3` - you can freely restart the bot without the need to manually reschedule message deletions.


## Installation

### 1. Get telegram token

1. Open Telegram
2. Talk to `@BotFather` and ask it to create a new bot
3. Save the HTTP API token that it gives you


### (Optional ) 2. Send a permanent message in the group

If all messages are deleted in a telegram group, telegram client will close and hide the group to the users until the client is restarted. This permanent message will prevent that from happening. Send it before adding the bot to the group.


### 3. Add the bot to your group

Invite the bot to your group and give it admin privileges (so it can read all messages, not just commands) with `Delete messages` permission (so it can delete those messages).


### 4. Deploy the bot to your server

```bash
# [Linux only] install python3-venv and python3-pip if not already installed
sudo apt-get install python3-venv python3-pip

# clone the repository
git clone https://github.com/slatinsky/telegram-autodelete-bot
cd telegram-autodelete-bot

# create virtual environment
python3 -m venv venv

# [Windows] activate virtual environment
venv\Scripts\activate

# [Linux] activate virtual environment
source venv/bin/activate

# Install dependencies
python3 -m pip install -r requirements.txt
```


### 5. Configure the bot

```bash
cp config.example.ini config.ini
nano config.ini
```

Fill in the following fields in `config.ini` - don't use quotes around the values:
- `token`: The token you got from `@BotFather`
- `seconds`: The number of seconds to wait before deleting messages (e.g. `60` for 1 minute)
- `chatid`: The ID of the group you want to use the bot in. Don't know the ID? Run the bot in the group and send any message. The bot will print the chat ID in the console.


### 6. Run the bot

Activate the virtual environment and run the bot

```bash
source venv/bin/activate
python3 main.py
```


### 7. (Optional) Create a systemd service to start the bot after a server reboot

```bash
sudo nano /etc/systemd/system/telegram-autodelete-bot.service
```

Replace `User`, `WorkingDirectory`, and `ExecStart` with your own values

```ini
[Unit]
Description=Telegram autodelete bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-autodelete-bot
ExecStart=/home/ubuntu/telegram-autodelete-bot/venv/bin/python /home/ubuntu/telegram-autodelete-bot/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```


```bash
# enable service
sudo systemctl enable telegram-autodelete-bot.service

# start service
sudo systemctl start telegram-autodelete-bot.service

# check status
sudo systemctl status telegram-autodelete-bot.service
```


## Extending the bot

See the `on_new_message` function in `main.py` if you want to change the behavior of the bot - provided are commented-out examples of filtering bad words, timed replies, and logging to a file


## License

GPL-3.0. See [LICENSE](LICENSE.txt) for more information.


## Contributing

Feel free to open issues and pull requests.

If you find this project useful, give it a star ⭐. Thank you!