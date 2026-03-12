const tabButtons = Array.from(document.querySelectorAll('.tab-button'));
const panels = Array.from(document.querySelectorAll('.panel'));

function activateTab(targetId) {
  tabButtons.forEach((button) => {
    button.classList.toggle('active', button.dataset.target === targetId);
  });
  panels.forEach((panel) => {
    panel.classList.toggle('active', panel.id === targetId);
  });
}

tabButtons.forEach((button) => {
  button.addEventListener('click', () => activateTab(button.dataset.target));
});

document.getElementById('theme-dark').addEventListener('click', () => {
  document.body.dataset.theme = 'dark';
});

document.getElementById('theme-light').addEventListener('click', () => {
  document.body.dataset.theme = 'light';
});
