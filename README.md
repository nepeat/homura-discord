# Homura - Yet another Discord bot

Homura is a personal Discord bot that I've decided to open source and try to make serious for the general public.

## Features
* Logging of user events to database
* Undeletion of messages in channels for admins
* Booru image searching
* ~~Semi~~ working implementation of a NSFL filter
* Spaghetti code

## Deployment
#### FIGURE OUT HOW TO MAKE THIS WORK FROM SCRATCH

## Gitlab runner setup
```
gitlab-runner register -n \
  --url https://gitlab.com/ \
  --registration-token REGISTRATION_TOKEN \
  --executor docker \
  --description "Bot Docker Runner" \
  --docker-image "docker:latest" \
  --docker-volumes /var/run/docker.sock:/var/run/docker.sock
```

## Thanks
Thanks goes to the many bot devs that have published their projects on GitHub for great examples on how to solve problems.
* discord.py (Rapptz)
* MusicBot (Rhino)
* Mee6 (Cookie)
* ???? (Zephy) **lol**
