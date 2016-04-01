import cgi
import datetime
import os
import urllib
import jinja2
import webapp2
import messageindex

from django.utils import simplejson
from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext import ndb


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

DEFAULT_TOPIC = 'chat'

def messages_key():
    """Constructs a Datastore key for the Messages table.
    """
    return ndb.Key('Messages', 'Public')


def sessions_key():
    """Constructs a Datastore key for the Sessions table.
    """
    return ndb.Key('Sessions', 'All')


class Author(ndb.Model):
    """Sub model for representing an author."""
    identity = ndb.StringProperty(indexed=False)
    nickname = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)
    
    
class Message(ndb.Model):
    """A main model for representing an individual sent Message."""
    author = ndb.StructuredProperty(Author)
    # Note that the date is the only indexed property.  This is because this
    # table is only used for displaying the stream of messages, all searches are
    # done using the Search API:
    date = ndb.DateTimeProperty()
    topic = ndb.StringProperty(indexed=False)
    content = ndb.StringProperty(indexed=False)


class Session(ndb.Model):
    """A main model for representing an user's session."""
    client_id = ndb.StringProperty(indexed=True)
    # Not used, only for making administration easier:
    email = ndb.StringProperty(indexed=False)


class MainPage(webapp2.RequestHandler):
    """Generates the main web page."""
    def get(self):
        user = users.get_current_user()
        if not user:
            # This should never happen, as AppEngine should only get to this
            # handler if the user is signed in.  But defense in depth applies...
            self.redirect(users.create_login_url(self.request.uri))
            return

        # If this user has not used the system before, add their user_id to the
        # table of IDs which we attempt to broadcast all messages to.  (Note
        # that once you are in this table, you never leave...  In an ideal world
        # we'd expire entries when people close the web page.)
        query = Session.query(Session.client_id == user.user_id())
        if not query.iter().has_next():
            session = Session(parent=sessions_key())
            session.client_id = user.user_id();
            session.email = user.email();
            session.put()

        # Just fetch the messages from the past day to populate the UI.  At some
        # point in the future we should make this customizable (perhaps after we
        # add search functionality).
        messages_query = Message.query(ancestor=messages_key()).filter(
            Message.date > (datetime.datetime.now() -
                            datetime.timedelta(days=1))
        ).order(Message.date)
        # Limit query to 10k messages in case something goes haywire.
        messages = messages_query.fetch(10000)

        topic = self.request.get('topic', DEFAULT_TOPIC)
        token = channel.create_channel(user.user_id());
            
        print "messages: " + str(messages)
        
        # FIXME: should clone messages array and cgi.escape all elements in it,
        # instead of relying upon JINJA to do this.  In the process, we can
        # replace newlines with <br> (see encode_message below for code).

        template_values = {
            'user': user,
            'messages': messages,
            'topic': urllib.quote_plus(topic),
            'token': token,
        }
        
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


def safeStrToInt(s):
    try:
        return int(s)
    except ValueError:
        return 10


class SearchPage(webapp2.RequestHandler):
    """Generates the search results page."""
    def get(self):
        self.post()

    def post(self):
        user = users.get_current_user()
        if not user:
            # This should never happen, as AppEngine should only get to this
            # handler if the user is signed in.  But defense in depth applies...
            self.redirect(users.create_login_url(self.request.uri))
            return

        query = self.request.get('query', '')
        num_results = safeStrToInt(self.request.get('num_results', '10'))

        urlsafe_keys = messageindex.find(query, num_results)

        results = []
        for urlsafe_key in urlsafe_keys:
            results.append(ndb.Key(urlsafe=urlsafe_key).get())

        template_values = {
            'query': query,
            'num_results': num_results,
            'results': results
        }

        template = JINJA_ENVIRONMENT.get_template('search.html')
        self.response.write(template.render(template_values))

class MessageBroadcast():
    """Given a message, broadcast it to all users who have opened the UI."""
    message = None

    def __init__(self, message):
        self.message = message

    def encode_message(self):
        struct_message = {
            'nickname': cgi.escape(self.message.author.nickname),
            'email': cgi.escape(self.message.author.email),
            'date': cgi.escape(str(self.message.date)),
            'topic': cgi.escape(self.message.topic),
            'content': cgi.escape(self.message.content).replace("\n", "<br>")
        }
        return simplejson.dumps(struct_message)

    def send_message(self, dest):
        str_message = self.encode_message()
        channel.send_message(dest, str_message)

    def send(self):
        # Iterate over all logged in users and attempt to forward the message to
        # them:
        session_query = Session.query(ancestor=sessions_key())
        for session in session_query:
            self.send_message(session.client_id)


class SendMessage(webapp2.RequestHandler):
    """Handler for the /send POST request."""
    def post(self):
        user = users.get_current_user()
        if not user:
            # This should never happen, as AppEngine should only get to this
            # handler if the user is signed in.  But defense in depth applies...
            self.redirect(users.create_login_url(self.request.uri))
            return

        # Create a Message and store it in the DataStore.
        #
        # We set the same parent key on the 'Message' to ensure each Message is
        # in the same entity group. Queries across the single entity group will
        # be consistent. However, the write rate to a single entity group should
        # be limited to ~1/second.
        message = Message(parent=messages_key())

        topic = self.request.get('topic', DEFAULT_TOPIC)
        message.topic = topic
        message.author = Author(
                identity=user.user_id(),
                nickname=user.nickname(),
                email=user.email())
        message.content = self.request.get('content')
        message.date = datetime.datetime.now()
        message_key = message.put()

        # Index the message so it is available for future searches:
        messageindex.add(message_key.urlsafe(), message)
        
        # Now that we've recorded the message in the DataStore, broadcast it to
        # all open clients.
        broadcast = MessageBroadcast(message)
        broadcast.send()

            
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/send', SendMessage),
    ('/search', SearchPage),
], debug=True)
