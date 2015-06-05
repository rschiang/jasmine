import slacker
import settings
import models as m
import json
from datetime import datetime
from pprint import PrettyPrinter

slack = slacker.Slacker(settings.SLACK_TOKEN)
pprint = PrettyPrinter().pprint

def type_name(instance):
    return instance.__class__.__name__

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
    to_delete = []
    for rel in rel_class.select().join(m.User).where(rel_class.channel == channel):
        if rel.user.identifier not in users:
            to_delete.append(rel)
        else:
            users.remove(rel.user.identifier)

    for i in to_delete:
        i.delete_instance()

    if users:
        rel_class.insert_many([{'user': all_users[i], 'channel': channel} for i in users]).execute()

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

def update_groups():
    users = get_users()
    groups = slack.groups.list().body['groups']
    for raw_channel in groups:
        try:
            channel = m.Group.get(m.Group.identifier == raw_channel['id'])
        except m.Group.DoesNotExist:
            channel = m.Group(identifier=raw_channel['id'])
        channel.name = raw_channel['name']
        channel.raw = json.dumps(raw_channel, ensure_ascii=False)
        channel.save()
        update_channel_users(channel, raw_channel['members'], users, m.UserGroup)

def update_ims():
    users = get_users()
    ims = slack.im.list().body['ims']
    for raw_channel in ims:
        try:
            channel = m.Im.get(m.Im.identifier == raw_channel['id'])
        except m.Im.DoesNotExist:
            channel = m.Im(identifier=raw_channel['id'])
        channel.user = users[raw_channel['user']]
        channel.raw = json.dumps(raw_channel, ensure_ascii=False)
        channel.save()


def get_messages(channel, count=None):
    has_more = True
    latest = None
    if isinstance(channel, m.Channel):
        fetch_func = slack.channels.history
    elif isinstance(channel, m.Group):
        fetch_func = slack.groups.history
    elif isinstance(channel, m.Im):
        fetch_func = slack.im.history

    while has_more:
        response = fetch_func(channel=channel.identifier, count=count, latest=latest).body
        has_more = response['has_more']
        messages = sorted(response['messages'], key=lambda x: x['ts'], reverse=True)
        if not messages:
            break
        for message in messages:
            yield message
        latest = messages[-1]['ts']

def get_latest_message(channel):
    return channel.messages.order_by(m.Message.timestamp.desc()).first()

def get_latest_timestamp(channel):
    message = get_latest_message(channel)
    return message.timestamp if message else None

def update_messages(channel):
    users = get_users()
    oldest = get_latest_timestamp(channel) or datetime.min
    count = 0
    if isinstance(channel, m.Channel):
        rel_class = m.ChannelMessage
    elif isinstance(channel, m.Group):
        rel_class = m.GroupMessage
    elif isinstance(channel, m.Im):
        rel_class = m.ImMessage

    for raw_message in get_messages(channel, count=100):
        try:
            message = m.Message(type=raw_message['type'])
            timestamp = datetime.fromtimestamp(float(raw_message['ts']))
            if oldest >= timestamp:
                break   # We've passed the end
            if 'user' in raw_message:
                message.user = users[raw_message['user']]
            elif 'comment' in raw_message:
                message.user = users[raw_message['comment']['user']]
            elif 'bot_id' in raw_message:
                message.user = users.get(raw_message['bot_id'])
            message.text = raw_message['text']
            message.timestamp = timestamp
            message.raw = json.dumps(raw_message, ensure_ascii=False)
            message.save()
            rel_class.create(channel=channel, message=message)
            count += 1
        except KeyError:
            print('⚠️ in {} {}'.format(type_name(channel).lower(), channel.name))
            pprint(raw_message)
            break
    print('✅  {} new messages in {} {}'.format(count, type_name(channel).lower(), channel.name))

def update_all_messages():
    # update_users()
    # update_channels()
    for channel in m.Channel.select():
        update_messages(channel)

def update_group_messages():
    update_groups()
    for group in m.Group.select():
        update_messages(group)

def update_im_messages():
    update_ims()
    for im in m.Im.select():
        update_messages(im)
