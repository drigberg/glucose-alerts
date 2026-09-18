sudo docker run -d --name signal-api --restart=always -p 8080:8080 \
    -v $HOME/.local/share/signal-api:/home/.local/share/signal-cli \
    -e 'MODE=native' bbernhard/signal-cli-rest-api