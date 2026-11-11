FROM eclipse-temurin:25-jdk-jammy AS build
WORKDIR /build

COPY gradlew settings.gradle.kts build.gradle.kts ./
COPY gradle ./gradle
RUN chmod +x gradlew && ./gradlew dependencies --no-daemon -q

COPY src ./src
RUN ./gradlew bootJar -x test --no-daemon -q

FROM eclipse-temurin:25-jre-jammy
WORKDIR /app

RUN useradd -r spring && mkdir data && chown spring:spring data
USER spring

COPY --from=build /build/build/libs/io-bound-*-SNAPSHOT.jar app.jar

EXPOSE 8080
VOLUME /app/data

ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "app.jar"]
