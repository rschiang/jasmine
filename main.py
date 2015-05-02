import slacker
import settings
import models as m
import json

slack = slacker.Slacker(settings.SLACK_TOKEN)

def update_users():
    members = slack.users.list().body['members']
    for member in members:
        try:
            user = m.User.get(m.User.identifier == member['id'])
        except m.User.DoesNotExist:
            user = m.User(identifier=member['id'])
        user.name = member['name']
        user.avatar = member['profile'].get('image_original') or member['profile']['image_192']
        user.raw = json.dumps(member)
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

    rel_class.insert_many([{'user': users[i], 'channel': channel} for i in users])

def update_channels():
    users = { u.identifier : u for u in m.User.select() }
    channels = slack.channels.list().body['channels']
    for raw_channel in channels:
        try:
            channel = m.Channel.get(m.Channel.identifier == raw_channel['id'])
        except m.Channel.DoesNotExist:
            channel = m.Channel(identifier=raw_channel['id'])
        channel.name = raw_channel['name']
        channel.raw = json.dumps(raw_channel)
        channel.save()
        update_channel_users(channel, raw_channel['members'], users, m.UserChannel)

def get_messages(channel, count=None):
    has_more = True
    latest = None
    while has_more:
        response = slack.channels.history(channel=channel, count=count, latest=latest).body
        has_more = response['has_more']
        latest = response['latest']
        for message in response['messages']:
            yield message
