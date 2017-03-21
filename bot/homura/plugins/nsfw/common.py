# coding=utf-8
API_ENDPOINTS = [
    # Danbooru based
    {
        "type": "danbooru",
        "endpoint": "https://e621.net/post/index.json",
        "friendly_name": "e621",
        "permalink": "https://e621.net/post/show/{}"
    },

    # Gelbooru based
    {
        "type": "gelbooru",
        "endpoint": "https://rule34.xxx/index.php",
        "friendly_name": "Rule 34",
        "permalink": "https://rule34.xxx/index.php?page=post&s=view&id={}"
    },
    {
        "type": "gelbooru",
        "endpoint": "https://gelbooru.com/index.php",
        "friendly_name": "Gelbooru",
        "permalink": "https://gelbooru.com/index.php?page=post&s=view&id={}"
    }
]

USER_AGENT = "github.com/nepeat/homura-discord | nepeat#6071 | This is discord bot. This is mistake."
