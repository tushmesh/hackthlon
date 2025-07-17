# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.

import azure.cognitiveservices.speech as speechsdk
import base64
import datetime
import html
import json
import numpy as np
import os
import pytz
import random
import re
import requests
import threading
import time
import torch
import traceback
import uuid
from flask import Flask, Response, render_template, request
from flask_socketio import SocketIO, join_room
from azure.identity import DefaultAzureCredential
#from openai import AzureOpenAI
from vad_iterator import VADIterator, int2float
from dotenv import load_dotenv

# --- NEW IMPORT: Import your GroceryConciergeApp ---
# Corrected import statement to match the actual backend file name
from grocery_concierge_backend import GroceryConciergeApp

print("START")

# Create the Flask app
app = Flask(__name__, template_folder='.')

# Create the SocketIO instance
socketio = SocketIO(app)

# NEW: Load environment variables from .env file
load_dotenv()

# Environment variables (keep existing ones if you still need them for other features)
# Speech resource (required)
speech_region = os.environ.get('SPEECH_REGION')  # e.g. westus2
print(f'speech_region: {speech_region}')
speech_key = os.environ.get('SPEECH_KEY')
print(f'speech_key: {speech_key}')
speech_private_endpoint = os.environ.get('SPEECH_PRIVATE_ENDPOINT')  # e.g. https://my-speech-service.cognitiveservices.azure.com/ (optional)  # noqa: E501
print(f'speech_private_endpoint: {speech_private_endpoint}')
speech_resource_url = os.environ.get('SPEECH_RESOURCE_URL')  # e.g. /subscriptions/6e83d8b7-00dd-4b0a-9e98-dab9f060418b/resourceGroups/my-rg/providers/Microsoft.CognitiveServices/accounts/my-speech (optional, only used for private endpoint)  # noqa: E501
print(f'speech_resource_url : {speech_resource_url }')
user_assigned_managed_identity_client_id = os.environ.get('USER_ASSIGNED_MANAGED_IDENTITY_CLIENT_ID')  # e.g. the client id of user assigned managed identity accociated to your app service (optional, only used for private endpoint and user assigned managed identity)  # noqa: E501
print(f'user_assigned_managed_identity_client_id : {user_assigned_managed_identity_client_id }')

# OpenAI resource (required for chat scenario) - You might not need this if your backend handles all LLM calls
azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')  # e.g. https://my-aoai.openai.azure.com/
print(f'azure_openai_endpoint: {azure_openai_endpoint }')
azure_openai_api_key = os.environ.get('AZURE_OPENAI_API_KEY') # Corrected to read from env var
print(f'azure_openai_api_key: {azure_openai_api_key }')
azure_openai_deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME')  # e.g. my-gpt-35-turbo-deployment
print(f'azure_openai_deployment_name : {azure_openai_deployment_name}')

# Cognitive search resource (optional, only required for 'on your data' scenario)
cognitive_search_endpoint = os.environ.get('COGNITIVE_SEARCH_ENDPOINT')  # e.g. https://my-cognitive-search.search.windows.net/
cognitive_search_api_key = os.environ.get('COGNITIVE_SEARCH_API_KEY')
cognitive_search_index_name = os.environ.get('COGNITIVE_SEARCH_INDEX_NAME')  # e.g. my-search-index
# Customized ICE server (optional, only required for customized ICE server)
ice_server_url = os.environ.get('ICE_SERVER_URL')  # The ICE URL, e.g. turn:x.x.x.x:3478
ice_server_url_remote = os.environ.get('ICE_SERVER_URL_REMOTE')  # The ICE URL for remote side, e.g. turn:x.x.x.x:3478. This is only required when the ICE address for remote side is different from local side.  # noqa: E501
ice_server_username = os.environ.get('ICE_SERVER_USERNAME')  # The ICE username
ice_server_password = os.environ.get('ICE_SERVER_PASSWORD')  # The ICE password

# Const variables
enable_websockets = True  # Enable websockets between client and server for real-time communication optimization
enable_vad = False  # Enable voice activity detection (VAD) for interrupting the avatar speaking
enable_token_auth_for_speech = False  # Enable token authentication for speech service
default_tts_voice = 'en-US-JennyMultilingualV2Neural'  # Default TTS voice
sentence_level_punctuations = ['.', '?', '!', ':', ';', '。', '？', '！', '：', '；']  # Punctuations that indicate the end of a sentence
enable_quick_reply = False  # Enable quick reply for certain chat models which take longer time to respond
quick_replies = ['Let me take a look.', 'Let me check.', 'One moment, please.']  # Quick reply reponses
oyd_doc_regex = re.compile(r'\[doc(\d+)\]')  # Regex to match the OYD (on-your-data) document reference
repeat_speaking_sentence_after_reconnection = True  # Repeat the speaking sentence after reconnection

# Global variables
client_contexts = {}  # Client contexts
speech_token = None  # Speech token
ice_token = None  # ICE token

# --- REMOVED: Global initialization of GroceryConciergeApp ---
# grocery_concierge_app = None

# Original AzureOpenAI client - keep if needed for other features, otherwise remove
if azure_openai_endpoint and azure_openai_api_key:
    azure_openai = AzureOpenAI(
        azure_endpoint=azure_openai_endpoint,
        api_version='2024-06-01',
        api_key=azure_openai_api_key)
else:
    azure_openai = None # Set to None if not configured

# VAD
vad_iterator = None
if enable_vad and enable_websockets:
    vad_model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
    vad_iterator = VADIterator(model=vad_model, threshold=0.5, sampling_rate=16000, min_silence_duration_ms=150, speech_pad_ms=100)

# --- REMOVED: Function to initialize the GroceryConciergeApp globally ---
# def initialize_grocery_concierge():
#     global grocery_concierge_app
#     if grocery_concierge_app is None:
#         grocery_concierge_app = GroceryConciergeApp()
#         grocery_concierge_app.initialize_backend()
#         print("GroceryConciergeApp backend initialized.")

# The default route, which shows the default web page (basic.html)
@app.route("/")
def index():
    # REMOVED: Call to global initialize_grocery_concierge
    return render_template("basic.html", methods=["GET"], client_id=initializeClient())


# The basic route, which shows the basic web page
@app.route("/basic")
def basicView():
    # REMOVED: Call to global initialize_grocery_concierge
    return render_template("basic.html", methods=["GET"], client_id=initializeClient())


# The chat route, which shows the chat web page
@app.route("/chat")
def chatView():
    # REMOVED: Call to global initialize_grocery_concierge
    return render_template("chat.html", methods=["GET"], client_id=initializeClient(), enable_websockets=enable_websockets)


# The API route to get the speech token
@app.route("/api/getSpeechToken", methods=["GET"])
def getSpeechToken() -> Response:
    response = Response(speech_token, status=200)
    response.headers['SpeechRegion'] = speech_region
    if speech_private_endpoint:
        response.headers['SpeechPrivateEndpoint'] = speech_private_endpoint
    return response


# The API route to get the ICE token
@app.route("/api/getIceToken", methods=["GET"])
def getIceToken() -> Response:
    # Apply customized ICE server if provided
    if ice_server_url and ice_server_username and ice_server_password:
        custom_ice_token = json.dumps({
            'Urls': [ice_server_url],
            'Username': ice_server_username,
            'Password': ice_server_password
        })
        return Response(custom_ice_token, status=200)
    return Response(ice_token, status=200)


# The API route to get the status of server
@app.route("/api/getStatus", methods=["GET"])
def getStatus() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    client_context = client_contexts[client_id]
    status = {
        'speechSynthesizerConnected': client_context['speech_synthesizer_connected']
    }
    return Response(json.dumps(status), status=200)


# The API route to connect the TTS avatar
@app.route("/api/connectAvatar", methods=["POST"])
def connectAvatar() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    isReconnecting = request.headers.get('Reconnect') and request.headers.get('Reconnect').lower() == 'true'
    # disconnect avatar if already connected
    disconnectAvatarInternal(client_id, isReconnecting)
    client_context = client_contexts[client_id]

    # Override default values with client provided values
    client_context['azure_openai_deployment_name'] = (
        request.headers.get('AoaiDeploymentName') if request.headers.get('AoaiDeploymentName') else azure_openai_deployment_name)
    client_context['cognitive_search_index_name'] = (
        request.headers.get('CognitiveSearchIndexName') if request.headers.get('CognitiveSearchIndexName')
        else cognitive_search_index_name)
    client_context['tts_voice'] = request.headers.get('TtsVoice') if request.headers.get('TtsVoice') else default_tts_voice
    client_context['custom_voice_endpoint_id'] = request.headers.get('CustomVoiceEndpointId')
    client_context['personal_voice_speaker_profile_id'] = request.headers.get('PersonalVoiceSpeakerProfileId')

    custom_voice_endpoint_id = client_context['custom_voice_endpoint_id']

    try:
        if speech_private_endpoint:
            speech_private_endpoint_wss = speech_private_endpoint.replace('https://', 'wss://')
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                speech_config = speechsdk.SpeechConfig(
                    endpoint=f'{speech_private_endpoint_wss}/tts/cognitiveservices/websocket/v1?enableTalkingAvatar=true')
                speech_config.authorization_token = speech_token
            else:
                speech_config = speechsdk.SpeechConfig(
                    subscription=speech_key,
                    endpoint=f'{speech_private_endpoint_wss}/tts/cognitiveservices/websocket/v1?enableTalkingAvatar=true')
        else:
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                speech_config = speechsdk.SpeechConfig(
                    endpoint=f'wss://{speech_region}.tts.speech.microsoft.com/cognitiveservices/websocket/v1?enableTalkingAvatar=true')
                speech_config.authorization_token = speech_token
            else:
                speech_config = speechsdk.SpeechConfig(
                    subscription=speech_key,
                    endpoint=f'wss://{speech_region}.tts.speech.microsoft.com/cognitiveservices/websocket/v1?enableTalkingAvatar=true')

        if custom_voice_endpoint_id:
            speech_config.endpoint_id = custom_voice_endpoint_id

        client_context['speech_synthesizer'] = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        speech_synthesizer = client_context['speech_synthesizer']

        ice_token_obj = json.loads(ice_token)
        # Apply customized ICE server if provided
        if ice_server_url and ice_server_username and ice_server_password:
            ice_token_obj = {
                'Urls': [ice_server_url_remote] if ice_server_url_remote else [ice_server_url],
                'Username': ice_server_username,
                'Credential': ice_server_password
            }
        local_sdp = request.data.decode('utf-8')
        avatar_character = request.headers.get('AvatarCharacter')
        avatar_style = request.headers.get('AvatarStyle')
        background_color = '#FFFFFFFF' if request.headers.get('BackgroundColor') is None else request.headers.get('BackgroundColor')
        background_image_url = request.headers.get('BackgroundImageUrl')
        is_custom_avatar = request.headers.get('IsCustomAvatar')
        transparent_background = (
            'false' if request.headers.get('TransparentBackground') is None
            else request.headers.get('TransparentBackground'))
        video_crop = 'false' if request.headers.get('VideoCrop') is None else request.headers.get('VideoCrop')
        avatar_config = {
            'synthesis': {
                'video': {
                    'protocol': {
                        'name': "WebRTC",
                        'webrtcConfig': {
                            'clientDescription': local_sdp,
                            'iceServers': [{
                                'urls': [ice_token_obj['Urls'][0]],
                                'username': ice_token_obj['Username'],
                                'credential': ice_token_obj['Password']
                            }]
                        },
                    },
                    'format': {
                        'crop': {
                            'topLeft': {
                                'x': 600 if video_crop.lower() == 'true' else 0,
                                'y': 0
                            },
                            'bottomRight': {
                                'x': 1320 if video_crop.lower() == 'true' else 1920,
                                'y': 1080
                            }
                        },
                        'bitrate': 1000000
                    },
                    'talkingAvatar': {
                        'customized': is_custom_avatar.lower() == 'true',
                        'character': avatar_character,
                        'style': avatar_style,
                        'background': {
                            'color': '#00FF00FF' if transparent_background.lower() == 'true' else background_color,
                            'image': {
                                'url': background_image_url
                            }
                        }
                    }
                }
            }
        }

        connection = speechsdk.Connection.from_speech_synthesizer(speech_synthesizer)
        connection.connected.connect(lambda evt: print('TTS Avatar service connected.'))

        def tts_disconnected_cb(evt):
            print('TTS Avatar service disconnected.')
            client_context['speech_synthesizer_connection'] = None
            client_context['speech_synthesizer_connected'] = False
            if enable_websockets:
                socketio.emit("response", {'path': 'api.event', 'eventType': 'SPEECH_SYNTHESIZER_DISCONNECTED'}, room=client_id)

        connection.disconnected.connect(tts_disconnected_cb)
        connection.set_message_property('speech.config', 'context', json.dumps(avatar_config))
        client_context['speech_synthesizer_connection'] = connection
        client_context['speech_synthesizer_connected'] = True
        if enable_websockets:
            socketio.emit("response", {'path': 'api.event', 'eventType': 'SPEECH_SYNTHESIZER_CONNECTED'}, room=client_id)

        speech_sythesis_result = speech_synthesizer.speak_text_async('').get()
        print(f'Result id for avatar connection: {speech_sythesis_result.result_id}')
        if speech_sythesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_sythesis_result.cancellation_details
            print(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"Error details: {cancellation_details.error_details}")
                raise Exception(cancellation_details.error_details)
        turn_start_message = speech_synthesizer.properties.get_property_by_name('SpeechSDKInternal-ExtraTurnStartMessage')
        remoteSdp = json.loads(turn_start_message)['webrtc']['connectionString']

        return Response(remoteSdp, status=200)

    except Exception as e:
        return Response(f"Result ID: {speech_sythesis_result.result_id}. Error message: {e}", status=400)


# The API route to connect the STT service
@app.route("/api/connectSTT", methods=["POST"])
def connectSTT() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    # disconnect STT if already connected
    disconnectSttInternal(client_id)
    system_prompt = request.headers.get('SystemPrompt')
    client_context = client_contexts[client_id]
    try:
        if speech_private_endpoint:
            speech_private_endpoint_wss = speech_private_endpoint.replace('https://', 'wss://')
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                speech_config = speechsdk.SpeechConfig(
                    endpoint=f'{speech_private_endpoint_wss}/stt/speech/universal/v2')
                speech_config.authorization_token = speech_token
            else:
                speech_config = speechsdk.SpeechConfig(
                    subscription=speech_key, endpoint=f'{speech_private_endpoint_wss}/stt/speech/universal/v2')
        else:
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                speech_config = speechsdk.SpeechConfig(
                    endpoint=f'wss://{speech_region}.stt.speech.microsoft.com/speech/universal/v2')
                speech_config.authorization_token = speech_token
            else:
                speech_config = speechsdk.SpeechConfig(
                    subscription=speech_key, endpoint=f'wss://{speech_region}.stt.speech.microsoft.com/speech/universal/v2')

        audio_input_stream = speechsdk.audio.PushAudioInputStream()
        client_context['audio_input_stream'] = audio_input_stream

        audio_config = speechsdk.audio.AudioConfig(stream=audio_input_stream)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        client_context['speech_recognizer'] = speech_recognizer

        speech_recognizer.session_started.connect(lambda evt: print(f'STT session started - session id: {evt.session_id}'))
        speech_recognizer.session_stopped.connect(lambda evt: print('STT session stopped.'))

        speech_recognition_start_time = datetime.datetime.now(pytz.UTC)

        def stt_recognized_cb(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                try:
                    user_query = evt.result.text.strip()
                    if user_query == '':
                        return

                    socketio.emit("response", {'path': 'api.chat', 'chatResponse': '\n\nUser: ' + user_query + '\n\n'}, room=client_id)
                    recognition_result_received_time = datetime.datetime.now(pytz.UTC)
                    speech_finished_offset = (evt.result.offset + evt.result.duration) / 10000
                    stt_latency = round((recognition_result_received_time - speech_recognition_start_time).total_seconds() * 1000 - speech_finished_offset)  # noqa: E501
                    print(f'STT latency: {stt_latency}ms')
                    socketio.emit("response", {'path': 'api.chat', 'chatResponse': f"<STTL>{stt_latency}</STTL>"}, room=client_id)
                    chat_initiated = client_context['chat_initiated']
                    if not chat_initiated:
                        initializeChatContext(system_prompt, client_id)
                        client_context['chat_initiated'] = True
                    first_response_chunk = True
                    
                    # --- MODIFIED: Call your client-specific GroceryConciergeApp for response ---
                    concierge_response = client_context['grocery_concierge_instance'].process_user_question(user_query)
                    
                    if first_response_chunk:
                        socketio.emit("response", {'path': 'api.chat', 'chatResponse': 'Assistant: '}, room=client_id)
                        first_response_chunk = False
                    socketio.emit("response", {'path': 'api.chat', 'chatResponse': concierge_response}, room=client_id)
                    # --- END MODIFIED ---

                except Exception as e:
                    print(f"Error in handling user query: {e}")
        speech_recognizer.recognized.connect(stt_recognized_cb)

        def stt_recognizing_cb(evt):
            if not vad_iterator:
                stopSpeakingInternal(client_id, False)
        speech_recognizer.recognizing.connect(stt_recognizing_cb)

        def stt_canceled_cb(evt):
            cancellation_details = speechsdk.CancellationDetails(evt.result)
            print(f'STT connection canceled. Error message: {cancellation_details.error_details}')
        speech_recognizer.canceled.connect(stt_canceled_cb)

        speech_recognizer.start_continuous_recognition()
        return Response(status=200)

    except Exception as e:
        return Response(f"STT connection failed. Error message: {e}", status=400)


# The API route to disconnect the STT service
@app.route("/api/disconnectSTT", methods=["POST"])
def disconnectSTT() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    try:
        disconnectSttInternal(client_id)
        return Response('STT Disconnected.', status=200)
    except Exception as e:
        return Response(f"STT disconnection failed. Error message: {e}", status=400)


# The API route to speak a given SSML
@app.route("/api/speak", methods=["POST"])
def speak() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    try:
        ssml = request.data.decode('utf-8')
        result_id = speakSsml(ssml, client_id, True)
        return Response(result_id, status=200)
    except Exception as e:
        return Response(f"Speak failed. Error message: {e}", status=400)


# The API route to stop avatar from speaking
@app.route("/api/stopSpeaking", methods=["POST"])
def stopSpeaking() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    stopSpeakingInternal(client_id, False)
    return Response('Speaking stopped.', status=200)


# The API route for chat
# It receives the user query and return the chat response.
# It returns response in stream, which yields the chat response in chunks.
@app.route("/api/chat", methods=["POST"])
def chat() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    client_context = client_contexts[client_id]
    chat_initiated = client_context['chat_initiated']
    if not chat_initiated:
        initializeChatContext(request.headers.get('SystemPrompt'), client_id)
        client_context['chat_initiated'] = True
    user_query = request.data.decode('utf-8')
    
    # --- MODIFIED: Call your client-specific GroceryConciergeApp for response ---
    concierge_response = client_context['grocery_concierge_instance'].process_user_question(user_query)
    # Speak the response
    try:
        speakWithQueue(concierge_response, 0, client_id)
    except Exception as e:
        print(f"Error in speaking response: {e}")
    return Response(concierge_response, mimetype='text/plain', status=200)
    # --- END MODIFIED ---


# The API route to continue speaking the unfinished sentences
@app.route("/api/chat/continueSpeaking", methods=["POST"])
def continueSpeaking() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    client_context = client_contexts[client_id]
    spoken_text_queue = client_context['spoken_text_queue']
    speaking_text = client_context['speaking_text']
    if speaking_text and repeat_speaking_sentence_after_reconnection:
        spoken_text_queue.insert(0, speaking_text)
    if len(spoken_text_queue) > 0:
        speakWithQueue(None, 0, client_id)
    return Response('Request sent.', status=200)


# The API route to clear the chat history
@app.route("/api/chat/clearHistory", methods=["POST"])
def clearChatHistory() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    client_context = client_contexts[client_id]
    # To clear the chat history for a specific client, we'll reset its GroceryConciergeApp instance's history.
    # Note: If initializeChatContext also manages this, ensure it's consistent.
    if 'grocery_concierge_instance' in client_context:
        client_context['grocery_concierge_instance'].chat_history.clear() # Clear backend history
    initializeChatContext(request.headers.get('SystemPrompt'), client_id) # This clears client-side 'messages'
    client_context['chat_initiated'] = True
    return Response('Chat history cleared.', status=200)


# The API route to disconnect the TTS avatar
@app.route("/api/disconnectAvatar", methods=["POST"])
def disconnectAvatar() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    try:
        disconnectAvatarInternal(client_id, False)
        return Response('Disconnected avatar', status=200)
    except Exception:
        return Response(traceback.format_exc(), status=400)


# The API route to release the client context, to be invoked when the client is closed
@app.route("/api/releaseClient", methods=["POST"])
def releaseClient() -> Response:
    client_id = uuid.UUID(json.loads(request.data)['clientId'])
    try:
        disconnectAvatarInternal(client_id, False)
        disconnectSttInternal(client_id)
        # Explicitly remove the GroceryConciergeApp instance
        if 'grocery_concierge_instance' in client_contexts[client_id]:
            del client_contexts[client_id]['grocery_concierge_instance']
        time.sleep(2)  # Wait some time for the connection to close
        client_contexts.pop(client_id)
        print(f"Client context released for client {client_id}.")
        return Response('Client context released.', status=200)
    except Exception as e:
        print(f"Client context release failed. Error message: {e}")
        return Response(f"Client context release failed. Error message: {e}", status=400)


@socketio.on("connect")
def handleWsConnection():
    client_id = uuid.UUID(request.args.get('clientId'))
    join_room(client_id)
    print(f"WebSocket connected for client {client_id}.")


@socketio.on("message")
def handleWsMessage(message):
    client_id = uuid.UUID(message.get('clientId'))
    path = message.get('path')
    client_context = client_contexts[client_id]

    if path == 'api.audio':
        chat_initiated = client_context['chat_initiated']
        audio_chunk = message.get('audioChunk')
        audio_chunk_binary = base64.b64decode(audio_chunk)
        audio_input_stream = client_context['audio_input_stream']
        if audio_input_stream:
            audio_input_stream.write(audio_chunk_binary)
        if vad_iterator:
            audio_buffer = client_context['vad_audio_buffer']
            audio_buffer.extend(audio_chunk_binary)
            if len(audio_buffer) >= 1024:
                audio_chunk_int = np.frombuffer(bytes(audio_buffer[:1024]), dtype=np.int16)
                audio_buffer.clear()
                audio_chunk_float = int2float(audio_chunk_int)
                vad_detected = vad_iterator(torch.from_numpy(audio_chunk_float))
                if vad_detected:
                    print("Voice activity detected.")
                    stopSpeakingInternal(client_id, False)

    elif path == 'api.chat':
        chat_initiated = client_context['chat_initiated']
        if not chat_initiated:
            initializeChatContext(message.get('systemPrompt'), client_id)
            client_context['chat_initiated'] = True

        user_query = message.get('userQuery')

        # --- MODIFIED: Call client-specific GroceryConciergeApp instance ---
        concierge_response = client_context['grocery_concierge_instance'].process_user_question(user_query)

        # Send the response in chunks (first the "Assistant: " prefix, then the actual response)
        socketio.emit("response", {'path': 'api.chat', 'chatResponse': 'Assistant: '}, room=client_id)
        socketio.emit("response", {'path': 'api.chat', 'chatResponse': concierge_response}, room=client_id)

        # Speak the response
        try:
            speakWithQueue(concierge_response, 0, client_id)
        except Exception as e:
            print(f"Error in speaking response: {e}")

# Initialize the client by creating a client id and an initial context
def initializeClient() -> uuid.UUID:
    client_id = uuid.uuid4()
    
    # Initialize a new GroceryConciergeApp instance for this client
    client_grocery_concierge_app = GroceryConciergeApp()
    client_grocery_concierge_app.initialize_backend() # Initialize its backend components

    client_contexts[client_id] = {
        'audio_input_stream': None,  # Audio input stream for speech recognition
        'vad_audio_buffer': [],  # Audio input buffer for VAD
        'speech_recognizer': None,  # Speech recognizer for user speech
        'azure_openai_deployment_name': azure_openai_deployment_name,  # Azure OpenAI deployment name
        'cognitive_search_index_name': cognitive_search_index_name,  # Cognitive search index name
        'tts_voice': default_tts_voice,  # TTS voice
        'custom_voice_endpoint_id': None,  # Endpoint ID (deployment ID) for custom voice
        'personal_voice_speaker_profile_id': None,  # Speaker profile ID for personal voice
        'speech_synthesizer': None,  # Speech synthesizer for avatar
        'speech_synthesizer_connection': None,  # Speech synthesizer connection for avatar
        'speech_synthesizer_connected': False,  # Flag to indicate if the speech synthesizer is connected
        'speech_token': None,  # Speech token for client side authentication with speech service
        'ice_token': None,  # ICE token for ICE/TURN/Relay server connection
        'chat_initiated': False,  # Flag to indicate if the chat context is initiated
        # Use 'messages' for client-side display history as it was already present
        'messages': [],  # Chat messages (history) for client-side display
        'data_sources': [],  # Data sources for 'on your data' scenario - This will no longer be used by your backend
        'is_speaking': False,  # Flag to indicate if the avatar is speaking
        'speaking_text': None,  # The text that the avatar is speaking
        'spoken_text_queue': [],  # Queue to store the spoken text
        'speaking_thread': None,  # The thread to speak the spoken text queue
        'last_speak_time': None,  # The last time the avatar spoke
        'grocery_concierge_instance': client_grocery_concierge_app # Store the client-specific instance
    }
    return client_id


# Refresh the ICE token every 24 hours
def refreshIceToken() -> None:
    global ice_token
    while True:
        ice_token_response = None
        if speech_private_endpoint:
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                ice_token_response = requests.get(
                    f'{speech_private_endpoint}/tts/cognitiveservices/avatar/relay/token/v1',
                    headers={'Authorization': f'Bearer {speech_token}'})
            else:
                ice_token_response = requests.get(
                    f'{speech_private_endpoint}/tts/cognitiveservices/avatar/relay/token/v1',
                    headers={'Ocp-Apim-Subscription-Key': speech_key})
        else:
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                ice_token_response = requests.get(
                    f'https://{speech_region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1',
                    headers={'Authorization': f'Bearer {speech_token}'})
            else:
                ice_token_response = requests.get(
                    f'https://{speech_region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1',
                    headers={'Ocp-Apim-Subscription-Key': speech_key})
        if ice_token_response.status_code == 200:
            ice_token = ice_token_response.text
        else:
            raise Exception(f"Failed to get ICE token. Status code: {ice_token_response.status_code}")
        time.sleep(60 * 60 * 24)  # Refresh the ICE token every 24 hours


# Refresh the speech token every 9 minutes
def refreshSpeechToken() -> None:
    global speech_token
    while True:
        # Refresh the speech token every 9 minutes
        if speech_private_endpoint:
            credential = DefaultAzureCredential(managed_identity_client_id=user_assigned_managed_identity_client_id)
            token = credential.get_token('https://cognitiveservices.azure.com/.default')
            speech_token = f'aad#{speech_resource_url}#{token.token}'
        else:
            speech_token = requests.post(
                f'https://{speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken',
                headers={'Ocp-Apim-Subscription-Key': speech_key}).text
        time.sleep(60 * 9)


# Initialize the chat context, e.g. chat history (messages), data sources, etc. For chat scenario.
# NOTE: This function's role changes. It no longer initializes chat history for the LLM itself,
# as your new backend handles that. It still sets up data sources if you were using them
# for the original Azure OpenAI 'on your data' feature.
def initializeChatContext(system_prompt: str, client_id: uuid.UUID) -> None:
    client_context = client_contexts[client_id]
    cognitive_search_index_name = client_context['cognitive_search_index_name']
    messages = client_context['messages'] # This list will no longer be used for LLM chat history
    data_sources = client_context['data_sources']

    # Initialize data sources for 'on your data' scenario (if you still need this for other features)
    data_sources.clear()
    if cognitive_search_endpoint and cognitive_search_api_key and cognitive_search_index_name:
        # On-your-data scenario
        data_source = {
            'type': 'azure_search',
            'parameters': {
                'endpoint': cognitive_search_endpoint,
                'index_name': cognitive_search_index_name,
                'authentication': {
                    'type': 'api_key',
                    'key': cognitive_search_api_key
                },
                'semantic_configuration': '',
                'query_type': 'simple',
                'fields_mapping': {
                    'content_fields_separator': '\n',
                    'content_fields': ['content'],
                    'filepath_field': None,
                    'title_field': 'title',
                    'url_field': None
                },
                'in_scope': True,
                'role_information': system_prompt
            }
        }
        data_sources.append(data_source)

    # Messages list is cleared but not used by the new backend's LLM
    messages.clear()
    # The system prompt is not directly used by the new backend's LLM for chat history
    # as it's embedded in the LLMService's prompt template.
    # If len(data_sources) == 0:
    #     system_message = {
    #         'role': 'system',
    #         'content': system_prompt
    #     }
    #     messages.append(system_message)


# Handle the user query and return the assistant reply. For chat scenario.
# The function is a generator, which yields the assistant reply in chunks.
# --- MODIFIED: This function now calls your client-specific GroceryConciergeApp instance ---
def handleUserQuery(user_query: str, client_id: uuid.UUID):
    client_context = client_contexts[client_id]
    
    # We no longer use Azure OpenAI directly here.
    # The `messages` and `data_sources` in client_context are not used for LLM interaction by your new backend.
    # If you still need `messages` for display purposes, you can manage them separately.
    # `data_sources` might still be relevant if you have other features relying on Cognitive Search.

    # For 'on your data' scenario, chat API currently has long (4s+) latency
    # We return some quick reply here before the chat API returns to mitigate.
    # This quick reply logic can be kept if desired, but it will precede your backend's response.
    if len(client_context['data_sources']) > 0 and enable_quick_reply:
        speakWithQueue(random.choice(quick_replies), 2000, client_id)

    # Call your integrated backend to process the user question
    # The `process_user_question` method in GroceryConciergeApp returns the final string answer.
    try:
        concierge_response = client_context['grocery_concierge_instance'].process_user_question(user_query)
        
        # Yield the response as a single chunk.
        # If your frontend expects streaming, you would need to modify
        # `GroceryConciergeApp.process_user_question` to be a generator
        # and yield chunks, then iterate here.
        yield concierge_response

        # Update chat history for display if needed (not for LLM input anymore)
        # client_context['messages'].append({'role': 'user', 'content': user_query})
        # client_context['messages'].append({'role': 'assistant', 'content': concierge_response})

    except Exception as e:
        print(f"Error processing user question with GroceryConciergeApp: {e}")
        yield "I'm sorry, I encountered an error while processing your request. Please try again."


# Speak the given text. If there is already a speaking in progress, add the text to the queue. For chat scenario.
def speakWithQueue(text: str, ending_silence_ms: int, client_id: uuid.UUID) -> None:
    client_context = client_contexts[client_id]
    spoken_text_queue = client_context['spoken_text_queue']
    is_speaking = client_context['is_speaking']
    if text:
        spoken_text_queue.append(text)
    if not is_speaking:
        def speakThread():
            spoken_text_queue = client_context['spoken_text_queue']
            tts_voice = client_context['tts_voice']
            personal_voice_speaker_profile_id = client_context['personal_voice_speaker_profile_id']
            client_context['is_speaking'] = True
            while len(spoken_text_queue) > 0:
                text = spoken_text_queue.pop(0)
                client_context['speaking_text'] = text
                try:
                    speakText(text, tts_voice, personal_voice_speaker_profile_id, ending_silence_ms, client_id)
                except Exception as e:
                    print(f"Error in speaking text: {e}")
                    break
                client_context['last_speak_time'] = datetime.datetime.now(pytz.UTC)
            client_context['is_speaking'] = False
            client_context['speaking_text'] = None
            print("Speaking thread stopped.")
        client_context['speaking_thread'] = threading.Thread(target=speakThread)
        client_context['speaking_thread'].start()


# Speak the given text.
def speakText(text: str, voice: str, speaker_profile_id: str, ending_silence_ms: int, client_id: uuid.UUID) -> str:
    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'>
                 <voice name='{voice}'>
                     <mstts:ttsembedding speakerProfileId='{speaker_profile_id}'>
                         <mstts:leadingsilence-exact value='0'/>
                         {html.escape(text)}
                     </mstts:ttsembedding>
                 </voice>
               </speak>"""  # noqa: E501
    if ending_silence_ms > 0:
        ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'>
                     <voice name='{voice}'>
                         <mstts:ttsembedding speakerProfileId='{speaker_profile_id}'>
                             <mstts:leadingsilence-exact value='0'/>
                             {html.escape(text)}
                             <break time='{ending_silence_ms}ms' />
                         </mstts:ttsembedding>
                     </voice>
                   </speak>"""  # noqa: E501
    return speakSsml(ssml, client_id, False)


# Speak the given ssml with speech sdk
def speakSsml(ssml: str, client_id: uuid.UUID, asynchronized: bool) -> str:
    speech_synthesizer = client_contexts[client_id]['speech_synthesizer']
    speech_sythesis_result = (
        speech_synthesizer.start_speaking_ssml_async(ssml).get() if asynchronized
        else speech_synthesizer.speak_ssml_async(ssml).get())
    if speech_sythesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_sythesis_result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Result ID: {speech_sythesis_result.result_id}. Error details: {cancellation_details.error_details}")
            raise Exception(cancellation_details.error_details)
    return speech_sythesis_result.result_id


# Stop speaking internal function
def stopSpeakingInternal(client_id: uuid.UUID, skipClearingSpokenTextQueue: bool) -> None:
    client_context = client_contexts[client_id]
    client_context['is_speaking'] = False
    if not skipClearingSpokenTextQueue:
        spoken_text_queue = client_context['spoken_text_queue']
        spoken_text_queue.clear()
    avatar_connection = client_context['speech_synthesizer_connection']
    if avatar_connection:
        avatar_connection.send_message_async('synthesis.control', '{"action":"stop"}').get()


# Disconnect avatar internal function
def disconnectAvatarInternal(client_id: uuid.UUID, isReconnecting: bool) -> None:
    client_context = client_contexts[client_id]
    stopSpeakingInternal(client_id, isReconnecting)
    time.sleep(2)  # Wait for the speaking thread to stop
    avatar_connection = client_context['speech_synthesizer_connection']
    if avatar_connection:
        avatar_connection.close()


# Disconnect STT internal function
def disconnectSttInternal(client_id: uuid.UUID) -> None:
    client_context = client_contexts[client_id]
    speech_recognizer = client_context['speech_recognizer']
    audio_input_stream = client_context['audio_input_stream']
    if speech_recognizer:
        speech_recognizer.stop_continuous_recognition()
        connection = speechsdk.Connection.from_recognizer(speech_recognizer)
        connection.close()
        client_context['speech_recognizer'] = None
    if audio_input_stream:
        audio_input_stream.close()
        client_context['audio_input_stream'] = None


# Start the speech token refresh thread
speechTokenRefereshThread = threading.Thread(target=refreshSpeechToken)
speechTokenRefereshThread.daemon = True
speechTokenRefereshThread.start()

# Start the ICE token refresh thread
iceTokenRefreshThread = threading.Thread(target=refreshIceToken)
iceTokenRefreshThread.daemon = True
iceTokenRefreshThread.start()

# --- MODIFIED: Main entry point to run the Flask app with SocketIO ---
# This ensures the web server starts and listens for incoming requests.
if __name__ == "__main__":
    # REMOVED: Global initialization of the backend
    # initialize_grocery_concierge()
    # Run the Flask app with SocketIO
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True) # debug=True for development, allow_unsafe_werkzeug=True for older Werkzeug versions
