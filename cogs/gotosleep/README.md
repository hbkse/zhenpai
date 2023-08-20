## history

So that I can remember why this doesnt make sense the next time I check it

```
the first iteration:
    create empty role called "gotosleep"
    set view_channel=False role override on every channel
    at correct times, give and remove "gotosleep" to users 

    why this doesn't work:
        if the channel has a different override that sets view_channel=True, then that one takes priority, 
        even if the gotosleep role is higher in the hierarchy

the second iteration:
    if you set user specific overrides on channels, they take priority over the role ones
    so, at correct times, set all channels in the server to have user->view_channel=False
    
    sounds pretty messy, if there's a lot of users and a lot of channels, it's a lot network calls and floods audit log
    i didn't bother implementing this

the third iteration:
    there's also an idea to save the list of roles the user had before, and then remove them all, and give gotosleep role
    then restore the roles
    sounds like there's a bug in there somewhere, so i don't want to bother

the fourth iteration:
    just use timeouts... it wasn't what i originally wanted because it still lets you read text channels and react
    it kicks them out of the vc if they're in one too

the fifth iteration:
    as a fallback, for admins/server owner, have the bot dm the person if they're caught sending messages or sitting in a vc
```