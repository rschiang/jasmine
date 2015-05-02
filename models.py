import peewee as p

db = p.SqliteDatabase('jasmine.db')

def init():
    db.connect()
    for model in [User, Channel, Group, Im, Message, UserChannel, UserGroup, ChannelMessage, GroupMessage, ImMessage]:
        model.create_table(fail_silently=True)
    # Create Slackbot user
    User.create(id=0, identifier='USLACKBOT', name='slackbot',
        avatar='https://slack-assets2.s3-us-west-2.amazonaws.com/10068/img/slackbot_192.png',
        raw=r'{"is_bot": true}')

# Common model definition
class BaseModel(p.Model):
    class Meta:
        database = db

# Core objects
class User(BaseModel):
    identifier = p.CharField(unique=True)
    name = p.CharField(unique=True)
    avatar = p.TextField(null=True)
    raw = p.TextField()

    @property
    def channels(self):
        return Channel.select().join(UserChannel).where(UserChannel.user == self)


class Channel(BaseModel):
    identifier = p.CharField(unique=True)
    name = p.CharField(unique=True)
    raw = p.TextField()

    @property
    def users(self):
        return User.select().join(UserChannel).where(UserChannel.channel == self)

    @property
    def messages(self):
        return Message.select().join(ChannelMessage).where(ChannelMessage.channel == self)


class Group(BaseModel):
    identifier = p.CharField(unique=True)
    name = p.CharField(unique=True)
    raw = p.TextField()

    @property
    def users(self):
        return User.select().join(UserGroup).where(UserGroup.channel == self)

    @property
    def messages(self):
        return Message.select().join(GroupMessage).where(GroupMessage.channel == self)


class Im(BaseModel):
    identifier = p.CharField(unique=True)
    user = p.ForeignKeyField(User, unique=True)
    raw = p.TextField()

    @property
    def messages(self):
        return Message.select().join(ImMessage).where(ImMessage.channel == self)


class Message(BaseModel):
    type = p.CharField()
    user = p.ForeignKeyField(User, null=True)
    text = p.TextField(null=True)
    timestamp = p.DateTimeField()
    raw = p.TextField()


# Relations
class UserChannel(BaseModel):
    user = p.ForeignKeyField(User)
    channel = p.ForeignKeyField(Channel)

class UserGroup(BaseModel):
    user = p.ForeignKeyField(User)
    channel = p.ForeignKeyField(Group)

class ChannelMessage(BaseModel):
    channel = p.ForeignKeyField(Channel)
    message = p.ForeignKeyField(Message, unique=True)

class GroupMessage(BaseModel):
    channel = p.ForeignKeyField(Group)
    message = p.ForeignKeyField(Message, unique=True)

class ImMessage(BaseModel):
    channel = p.ForeignKeyField(Im)
    message = p.ForeignKeyField(Message, unique=True)
