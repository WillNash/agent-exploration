FROM node:20-alpine

# WORKDIR /app matches the bind-mount ./frontend/src:/app/src in docker-compose,
# enabling Vite hot-reload on host file changes.
WORKDIR /app

COPY frontend/package*.json ./

RUN npm install

COPY frontend/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
