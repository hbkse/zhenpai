### Twitcasting Cog

#### Overview
The Twitcasting cog notifies text channels whenever a
subscribed Twitcasting user starts or stops a livestream. Users can subscribe
to Twitcasting users to receive these notifications. Users can also search for
Twitcasting users via search terms.

#### Receiving Webhooks
Whenever a Twitcast user goes live or ends a stream, the Twitcasting API sends
a POST request to the configured webhook URL endpoint. The web server hosted by
the bot will intercept the request, parse the payload, and send notifications to
the subscribed text channels.

#### Commands
To use this cog, each subcommand has to preceded by `z!tc`.
* `z!tc search <arg1> <arg2> ...`: Searches Twitcasting for up to three users that
closely matches the provided query.
* `z!tc add <twitcasting-user-id> #<channel-name>(optional)`: Adds subscription of the
Twitcasting user to the provided text channel. If #<channel-name> is left blank,
then the channel in which the command was sent is used instead.
* `z!tc list #<channel-name>(optional)`: Lists all Twitcasting users that this
guild or text channel has subscribed to. If #<channel-name> is left blank,
then the command will list subscriptions for the entire guild/server instead.
* `z!tc remove <twitcasting-user-id> #<channel-name(optional)`: Removes subscription of the
Twitcasting user from the text channel. If #<channel-name> is left blank, then the 
channel in which the command was sent is used instead.
* `z!tc clear #<channel-name>`: Deletes any subscriptions in the text channel.

#### Maintenance
The cog is a Twitcasting application linked with an existing Twitcasting account
to access the Twitcasting API, subscribe to webhook notifications, and receive
webhook events. The Twitcasting application needs to be authenticated with
Twitcasting accounts every three months via either the 
[OAuth 2.0 Authorization Code Grant method](https://apiv2-doc.twitcasting.tv/#authorization-code-grant)
or the [OAuth 2.0 Implicit method](https://apiv2-doc.twitcasting.tv/#implicit).
To authenticate the application, a maintainer has to manually do the following procedure:

##### Manually Getting OAuth Access Token (Implicit Method) 

1. Login into a Twitcasting account.
2. Enter the following URL:
`https://apiv2.twitcasting.tv/oauth2/authorize?client_id={YOUR_CLIENT_ID}&response_type=token`
where `{YOUR_CLIENT_ID}` is substituted with the `CLIENT_ID` of the application. 
3. Click on the blue button `連携アプリを許可` (Link Application) to retrieve the token. The
website will now redirect you to a URL containing the OAuth token.
4. Copy the token string from the URL the website redirects you to.
5. Update the token string on Github Secrets under the key name `TWITCAST_ACCESS_TOKEN`.
    
