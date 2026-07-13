FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build
ENV PORT=3600
EXPOSE 3600
CMD ["npm", "run", "start"]
