FROM eclipse-temurin:25-jdk-jammy AS build
WORKDIR /app

COPY gradlew gradlew.bat ./
COPY gradle ./gradle

COPY build.gradle.kts settings.gradle.kts ./

RUN chmod +x gradlew && ./gradlew dependencies --no-daemon

COPY src ./src
RUN ./gradlew bootJar -x test --no-daemon

FROM eclipse-temurin:25-jre-jammy
WORKDIR /app

RUN useradd -m springuser && chown -R springuser:springuser /app
USER springuser

COPY --from=build /app/build/libs/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
