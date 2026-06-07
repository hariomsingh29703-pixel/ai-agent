const express = require('express');
const app = express();
const port = 3000;

app.use(express.json());

let todos = [];

app.post('/todos', (req, res) => {
  const { text } = req.body;
  todos.push({ text, completed: false });
  res.send(`Todo added: ${text}`);
});

app.get('/todos', (req, res) => {
  res.send(todos);
});

app.put('/todos/:index', (req, res) => {
  const { index } = req.params;
  todos[index].completed = true;
  res.send(`Todo completed: ${todos[index].text}`);
});

app.listen(port, () => {
  console.log(`Server started on port ${port}`);
});