FROM maven:3.9.9-eclipse-temurin-17-alpine AS build
WORKDIR /build

# Dependências em camada própria: só baixam de novo quando o pom.xml muda
COPY pom.xml ./
RUN mvn -B -q dependency:go-offline

COPY src ./src
RUN mvn -B -q package -DskipTests \
    && java -Djarmode=tools -jar target/cpu-bound.jar extract --layers --destination extracted

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

RUN addgroup -S spring && adduser -S spring -G spring
USER spring

# Da camada que menos muda para a que mais muda
COPY --from=build /build/extracted/dependencies/ ./
COPY --from=build /build/extracted/spring-boot-loader/ ./
COPY --from=build /build/extracted/snapshot-dependencies/ ./
COPY --from=build /build/extracted/application/ ./

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD wget -q -O /dev/null "http://localhost:${SERVER_PORT:-8080}/health" || exit 1

# exec: a JVM vira o PID 1 e recebe o SIGTERM do docker stop
ENTRYPOINT ["sh", "-c", "exec java -XX:MaxRAMPercentage=75 $JAVA_OPTS -jar cpu-bound.jar"]
