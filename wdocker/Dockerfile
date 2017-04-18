FROM alpine:3.5

MAINTAINER Jakob Antonsson <jakobant@gmail.com>

RUN echo "http://dl-4.alpinelinux.org/alpine/edge/community/" >> /etc/apk/repositories && \
    echo "http://dl-4.alpinelinux.org/alpine/edge/testing/" >> /etc/apk/repositories && \
    apk add --update openvpn openssl python py-virtualenv bash && \
    rm -rf /tmp/* /var/tmp/* /var/cache/apk/* /var/cache/distfiles/*

# Needed by scripts
ENV OPENVPN /etc/openvpn

EXPOSE 1194/udp
RUN mkdir /code
RUN mkdir /code/templates
RUN mkdir /store
RUN pip install jinja2
RUN pip install flask-HTTPAuth
CMD ["/start.sh"]

ADD ./wasy.py /code
ADD ./server.py /code
ADD ./template.ovpn /code
ADD ./openssl.cnf /code
ADD ./templates/index.html /code/templates
ADD ./templates/base.html /code/templates
ADD ./start.sh /
RUN chmod 755 /start.sh
