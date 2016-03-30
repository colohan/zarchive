// Allow a form to post without navigating to another page:
postForm = function(oFormElement) {
    if (!oFormElement.action) { return; }
    var oReq = new XMLHttpRequest();
    if (oFormElement.method.toLowerCase() === "post") {
        oReq.open("post", oFormElement.action);
        oReq.send(new FormData(oFormElement));
    } else {
        console.error("Can only use post with this!");
    }
}

// Make it so ctrl-Enter can send a message:
onKeyDown = function(e) {
    var keynum;
    var keychar;
    var numcheck;
    keynum = e.keyCode;

    if (e.ctrlKey && (keynum == 13 || // ctrl-Enter
		      keynum == 77)) // ctrl-M (ctrl-Enter on mac firefox does this)
    {
	postForm(document.forms["messageForm"]);
	document.getElementById('content').value='';
	return false;
    }
    return true;
}

// Called every time a new message shows up from the server:
onMessage = function(m) {
    // Parse the message received from the server:
    message = JSON.parse(m.data);

    // Then simply append it to our list of messages:
    document.getElementById("messages").innerHTML = 
        document.getElementById("messages").innerHTML +
        "<b>" + message.nickname + " (" + message.email + ") (" +
        message.topic + ") [" + message.date + "]</b><blockquote>" +
        message.content + "</blockquote>";
}

// Initialization, called once upon page load:
openChannel = function() {
    var channel = new goog.appengine.Channel(token);
    var handler = {
        'onopen': function() {},
        'onmessage': onMessage,
        'onerror': function() {},
        'onclose': function() {}
    };
    var socket = channel.open(handler);
    //socket.onopen = onOpened;
    socket.onmessage = onMessage;
}

setTimeout(openChannel, 100);
