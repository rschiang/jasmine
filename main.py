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

def update_channels():
    channels = slack.channels.list().body['channels']
    users = { u.identifier : u for u in m.User.select() }
    for raw_channel in channels:
        try:
            channel = m.Channel.get(m.Channel.identifier == raw_channel['id'])
        except m.Channel.DoesNotExist:
            channel = m.Channel(identifier=raw_channel['id'])
        channel.name = raw_channel['name']
        channel.raw = json.dumps(raw_channel)
        channel.save()

        current_users = [u.identifier for u in m.User.select().join(m.UserChannel).where(m.UserChannel.channel == channel)]
        m.UserChannel.insert_many([{'user': users[i], 'channel': channel} for i in raw_channel['members'] if i not in current_users])
        m.UserChannel.delete().join(m.User).where(m.User.identifier << set(current_users).difference(raw_channel['members']))
