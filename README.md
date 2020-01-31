
# Running the project locally
To build the bot run `sup local local_build` to build.    
To train the bot run `sup local train`  
To start a debug shell `sup local debug` or if you're on windows
debug.bat and then python main.py 


# Networking
Viber requires the bot have an internet facing url with https.
You can specify that in the VIBER_HOSTNAME environment variable.  
All events from viber are sent to that url.
Make sure it points to the bot. You might use Nginx with proxy_pass to help you out.

# Viber
First you'll need to create a bot.
GO here: https://partners.viber.com/account/create-bot-account
You'll need the Token from the created bot
Use these docs to develop your bot: https://developers.viber.com/docs/api/rest-bot-api/#get-started
Since the docs aren`t always complete, this project can help a bit: https://github.com/mileusna/viber