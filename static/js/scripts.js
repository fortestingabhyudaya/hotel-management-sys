// Example: Add subtle hover animation for buttons
document.querySelectorAll('a').forEach(btn => {
  btn.addEventListener('mouseenter', () => {
    btn.classList.add('scale-105');
  });
  btn.addEventListener('mouseleave', () => {
    btn.classList.remove('scale-105');
  });
});