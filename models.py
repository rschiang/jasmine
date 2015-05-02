import peewee as p

db = p.SqliteDatabase('jasmine.db')

# Common model definition
class BaseModel(p.Model):
    class Meta:
        database = db

# Core objects
class User(BaseModel):
    identifier = p.CharField(unique=True)
    name = p.CharField(unique=True)
    avatar = p.TextField()
    raw = p.TextField()

class Channel(BaseModel):
    identifier = p.CharField(unique=True)
    name = p.CharField(unique=True)
    raw = p.TextField()

class Group(BaseModel):
    identifier = p.CharField(unique=True)
    name = p.CharField(unique=True)
    raw = p.TextField()

class Im(BaseModel):
    identifier = p.CharField(unique=True)
    user = p.ForeignKeyField(User, unique=True)
    raw = p.TextField()

class Message(BaseModel):
    type = p.CharField()
    user = p.ForeignKeyField(User)
    text = p.TextField(null=True)
    timestamp = p.DateTimeField()
    raw = p.TextField()

# Relations
class UserChannel(BaseModel):
    user = p.ForeignKeyField(User)
    channel = p.ForeignKeyField(Channel)

class ChannelMessage(BaseModel):
    channel = p.ForeignKeyField(Channel)
    message = p.ForeignKeyField(Message, unique=True)

class GroupMessage(BaseModel):
    group = p.ForeignKeyField(Group)
    message = p.ForeignKeyField(Message, unique=True)

class ImMessage(BaseModel):
    im = p.ForeignKeyField(Im)
    message = p.ForeignKeyField(Message, unique=True)
