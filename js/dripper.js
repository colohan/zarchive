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
        "<div class=\"message\"<b>" + message.nickname + " (" + message.email + ") (" +
        message.topic + ") [" + message.date + "]</b><blockquote>" +
        message.content + "</blockquote></div>";
}

onOpen = function() {
    console.log("Channel to server opened.");
}

onError = function(e) {
    console.log("Error taking to server: " + e.description + " [code: " +
		e.code + "].");
}

onClose = function() {
    console.log("Channel to server closed");
    
    // Just retry:
    openChannel();
}

// Initialization, called once upon page load:
openChannel = function() {
    var channel = new goog.appengine.Channel(token);
    var handler = {
        'onopen': onOpen,
        'onmessage': onMessage,
        'onerror': onError,
        'onclose': onClose
    };
    var socket = channel.open(handler);
}

fetchMoreMessages = function() {
    document.getElementById("messages").innerHTML = 
	"<div class=\"message\"><b>fake top message (fake@fake.com) (fake.topic) [1999-01-01 12:00:00.000000]</b><blockquote>This is a fake message.</blockquote></div>" +
	document.getElementById("messages").innerHTML;
}

onScroll = function() {
    // If the user scrolls up to the top of the window, load some older
    // messages to display for them and insert them into the top.
    if ($(window).scrollTop() == 0){
//	// Attempted way of making the window not scroll as we insert new
//	// messages at the top.  For some reason we occasionally get multiple
//	// scroll events() with scrollTop() == 0, which makes this code fail.  I
//	// clearly don't know javascript well enough, as my attempts to fix have
//	// failed.  Feel free to tell me how to fix this if you are reading
//	// this.  :-)
//	document.getElementById("scratch_space").innerHTML = 
//	    document.getElementById("messages").innerHTML;
//
//	height_before = $(scratch_space).height();
//
//	document.getElementById("scratch_space").innerHTML = 
//	    "<b>fake top message (fake@fake.com) (fake.topic) [1999-01-01 12:00:00.000000]</b><blockquote>This is a fake message.</blockquote>" +
//	    document.getElementById("messages").innerHTML;
//
//
//	height_after = $(scratch_space).height();
//	document.getElementById("scratch_space").innerHTML = "";
//	console.log("height_before=" + height_before + " height_after=" + height_after);
//
//	new_scroll_position = height_after - height_before;
//	if (new_scroll_position > 0) {
//	    //$(window).off("scroll", onScroll);
//	    //$(window).on("scroll", eatScrollEvent);
//
//	    $(window).scrollTop(new_scroll_position);
//	    console.log("new_scroll_position=" + new_scroll_position);
//	}
//
//	fetchMoreMessages();
	fake = "<div class=\"message\"><b title=\"fake@fake.com\">fake top message (fake.topic) [1999-01-01 12:00:00.000000]</b><br>This is a fake message.</div>";
	$(".message").first().before(fake + fake + fake + fake + fake + fake + fake + fake + fake + fake);
	$(window).scrollTop($(".message").first().height() * 10);
    }
}

// Invoked by jQuery once the DOM is constructed:
$(function () {
    // Set callback to invoke when window scrolls:
    $(window).on("scroll", onScroll);

    // Scroll to bottom of document
    $(window).scrollTop($(document).height() - $(window).height());
    
    // Open channel back to server to get new messages:
    openChannel();
});
