import slacker
import settings
import models as m
import json
from datetime import datetime
from pprint import PrettyPrinter

slack = slacker.Slacker(settings.SLACK_TOKEN)
pprint = PrettyPrinter().pprint

def update_users():
    members = slack.users.list().body['members']
    for member in members:
        try:
            user = m.User.get(m.User.identifier == member['id'])
        except m.User.DoesNotExist:
            user = m.User(identifier=member['id'])
        user.name = member['name']
        user.avatar = member['profile'].get('image_original') or member['profile']['image_192']
        user.raw = json.dumps(member, ensure_ascii=False)
        user.save()

def update_channel_users(channel, users, all_users, rel_class):
    users = set(users)
    to_delete = []
    for rel in rel_class.select().join(m.User).where(rel_class.channel == channel):
        if rel.user.identifier not in users:
            to_delete.append(rel)
        else:
            users.remove(rel.user.identifier)

    for i in to_delete:
        i.delete_instance()

    rel_class.insert_many([{'user': all_users[i], 'channel': channel} for i in users])

def update_channels():
    users = get_users()
    channels = slack.channels.list().body['channels']
    for raw_channel in channels:
        try:
            channel = m.Channel.get(m.Channel.identifier == raw_channel['id'])
        except m.Channel.DoesNotExist:
            channel = m.Channel(identifier=raw_channel['id'])
        channel.name = raw_channel['name']
        channel.raw = json.dumps(raw_channel, ensure_ascii=False)
        channel.save()
        update_channel_users(channel, raw_channel['members'], users, m.UserChannel)

def get_users():
    return { u.identifier : u for u in m.User.select() }

def get_messages(channel, count=None):
    has_more = True
    latest = None
    while has_more:
        response = slack.channels.history(channel=channel.identifier, count=count, latest=latest).body
        has_more = response['has_more']
        messages = sorted(response['messages'], key=lambda x: x['ts'], reverse=True)
        for message in messages:
            yield message
        latest = messages[-1]['ts']

def update_messages(channel):
    users = get_users()
    for raw_message in get_messages(channel, count=400):
        try:
            message = m.Message(type=raw_message['type'])
            if 'user' in raw_message:
                message.user = users[raw_message['user']]
            elif 'comment' in raw_message:
                message.user = users[raw_message['comment']['user']]
            elif 'bot_id' in raw_message:
                message.user = users.get(raw_message['bot_id'])
            message.text = raw_message['text']
            message.timestamp = datetime.fromtimestamp(float(raw_message['ts']))
            message.raw = json.dumps(raw_message, ensure_ascii=False)
            message.save()
            m.ChannelMessage.create(channel=channel, message=message)
        except KeyError:
            print('⚠️ In channel {}'.format(channel.name))
            pprint(raw_message)
            break

def update_all_messages():
    # update_users()
    # update_channels()
    for channel in m.Channel.select():
        update_messages(channel)
