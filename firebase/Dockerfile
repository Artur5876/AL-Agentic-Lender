# Firebase emulators (Auth + Firestore + UI) for the local stack (US-341).
FROM eclipse-temurin:21-jre AS java
FROM node:22-bookworm-slim
COPY --from=java /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk PATH="/opt/java/openjdk/bin:${PATH}"
RUN npm install -g firebase-tools@15.34.1
WORKDIR /firebase
COPY firebase.json .firebaserc firestore.rules firestore.indexes.json ./
# Download the emulator jars at build time so start-up is fast.
RUN firebase setup:emulators:firestore && firebase setup:emulators:ui
EXPOSE 4000 8080 9099
CMD ["firebase", "emulators:start", "--project", "demo-al-group11"]
