FROM node:22-alpine

ENV TZ=Asia/Shanghai

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apk add --no-cache \
        file \
        patch \
        python3 \
        openssl \
        squashfs-tools

WORKDIR /app

COPY . .

RUN npm install

CMD ["npm", "run", "build"]