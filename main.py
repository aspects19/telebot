import requests
import time
import openai
import telebot
from telebot import types, apihelper


bot = telebot.TeleBot("7164315845:AAEUTeFjhukT-KabsOm57nc_yrM8nBM9Y") #Use your own
ACCUWEATHER_API_KEY = "xArFlO4D9JWAOcXsbAFAwW3qJrObc2q3" "Qeh1dKVuMMeoBAjH9eruJ13L6vyJT" #use your own

engine = None
conversations = {}

# Start handler
@bot.message_handler(commands=['start'])
def options(message):
    user = message.from_user
    first_name = user.first_name
    user_chat_id = message.chat.id
    channel_id = "-1001904236715"
    
    member_status = bot.get_chat_member(chat_id=channel_id,user_id=user_chat_id)
    if member_status.status == "member" or member_status.status == "creator":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Chat Mode", callback_data='chat_mode'),
            types.InlineKeyboardButton('Pic Generator', callback_data='pic_generator'),
            types.InlineKeyboardButton("Weather Update", callback_data="weather_update"),
            types.InlineKeyboardButton('Story completion', callback_data='story_completion')
        )

        bot.send_message(message.from_user.id, f"Hello 👋 {first_name}, choose the mode you want to use", reply_markup=markup)
        bot.send_message(message.from_user.id, "Hit /start to reset the mode you're using")
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("Subscribe to channel", url="tg://resolve?domain=flairbot_store"))
        bot.send_message(message.chat.id, "Subscribe to @flairbot_store to use the functionalities of this bot", reply_markup=markup)

        
# Button clicks handler
@bot.callback_query_handler(func=lambda call: True)
def answer(call):
    global engine

    if call.data == 'chat_mode':
        bot.send_message(call.message.chat.id, "Let's start chatting")
        engine = "text-davinci-003"

    elif call.data == 'pic_generator':
        bot.send_message(call.message.chat.id, "Send a text prompt and I'll generate a corresponding image")
        engine = 'dalle'

    elif call.data == 'weather_update':
        bot.send_message(call.message.chat.id, "Send a location and I'll provide its realtime weather")
        engine = 'weather'

    elif call.data == 'story_completion':
        bot.send_message(call.message.chat.id, "Send a the first few lines of a story and I will complete it \nDon't forget to include he number of words in the story you want generated")
        engine = 'story'

    elif call.data == None:
        bot.send_message(call.chat.id, 'Choose a mode you would like to use')


# clear previous conversations
@bot.message_handler(commands=["clear"])

def chat_history_clearer(message):
    chat_id = message.from_user.id
    if message.from_user.id in conversations:
        conversations[chat_id] = []
        bot.send_message(message.from_user.id, "Your chat history has been cleared")
    else:
        bot.send_message(message.from_user.id, "You have no previous conversations")


# Message handler
@bot.message_handler( content_types=['text'])
def requests_handler(message):
    global engine

    if engine == 'text-davinci-003':
        user_message = message.text
        chat_id = message.from_user.id

        if chat_id in conversations:
            prev_conversations = conversations[chat_id]
            context = "\n".join(prev_conversations[-4:])  # Include the last four conversations
            prompt = f"{context}\nUser: {user_message}\n"
        else:
            prompt = f"User: {user_message}\n"

        # System role append
        prompt_with_system_role = f"You're an assistant made by AM Jeff\n{prompt}"

        # response generator
        response = openai.Completion.create(
            engine='text-davinci-003',
            prompt=prompt_with_system_role,
            temperature=0.7,
            max_tokens=50,
            n=1,
            stop=None
        )
        bot_response = response.choices[0].text.strip().replace("Bot: ", "")

# Store current conversation
        if chat_id in conversations:
            conversations[chat_id].append(f"User: {user_message}")
            conversations[chat_id].append(f"Bot: {bot_response}")
        else:
            conversations[chat_id] = [f"User: {user_message}", f"Bot: {bot_response}"]
        time.sleep(1.0)
        bot.send_message(chat_id, bot_response)


    elif engine == 'story':
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f'"""complete the story that start with \n{message.text} in 400 words"""',
            temperature=0.7,
            max_tokens=2000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=['"""']
        )

        bot.send_chat_action(message.chat.id, "typing")
        time.sleep(1)
        bot.send_message(message.from_user.id, f'{response.choices[0].text}', parse_mode="None")

    elif engine == "dalle":
        response = openai.Image.create(
            prompt=f'"""{message.text}"""',
            n=1,
            size="512x512"
        )

        image_url = response.data[0].url
        bot.send_chat_action(message.chat.id, "upload_photo")
        time.sleep(1)
        bot.send_photo(message.from_user.id, image_url)

    elif engine == "weather":
        url = f'http://dataservice.accuweather.com/locations/v1/search?q={message.text}&apikey={ACCUWEATHER_API_KEY}'
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data:
                location_data = data[0]
                location_key = location_data.get('Key')
                region = location_data['Region']['EnglishName']
                country = location_data['Country']['EnglishName']

                # Weather data fetcher
                url = f'http://dataservice.accuweather.com/currentconditions/v1/{location_key}?apikey={ACCUWEATHER_API_KEY}'
                response = requests.get(url)

                if response.status_code == 200:
                    data = response.json()
                    if data:
                        weather_data = data[0]
                        weather_text = weather_data.get('WeatherText', None)
                        temperature = weather_data['Temperature']['Metric']['Value']
                        precipitation = "There is no Precipitation" if not weather_data['HasPrecipitation'] else f"Current precipitation is {weather_data['PrecipitationType']}"
                        bot.send_chat_action(message.chat.id, 'typing')
                        time.sleep(1)
                        bot.send_message(message.from_user.id, f"Region: {region}\nCountry: {country}\nWeather: {weather_text}\nTemperature: {temperature}°C\n{precipitation}")
            else:
                bot.send_chat_action(message.chat.id, 'typing')
                time.sleep(1)
                bot.send_message(message.chat.id, f"Weather data for {message.text} unavailable")
        else:
            bot.send_chat_action(message.chat.id, 'typing')
            time.sleep(1)
            bot.send_message(message.chat.id, "Some error occurred while processing your request")

    elif engine == None:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("Subscribe to channel", url="tg://resolve?domain=flairbot_store"))
        bot.send_message(message.chat.id, "Subscribe to @flairbot_store to use the functionalities of this bot", reply_markup=markup)


bot.infinity_polling()
