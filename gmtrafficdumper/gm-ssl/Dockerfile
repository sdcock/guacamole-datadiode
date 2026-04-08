FROM guacamole/guacamole
USER root
COPY ./guacd.crt /tmp/guacd.crt
RUN keytool -import -alias guacd-cert -file /tmp/guacd.crt \
    -keystore /opt/java/openjdk/lib/security/cacerts -storepass changeit -noprompt
USER guacamole
