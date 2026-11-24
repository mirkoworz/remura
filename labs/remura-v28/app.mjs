import { mountExperience } from './experience.mjs';
import { mountMarkets } from './markets.mjs';

const links = [...document.querySelectorAll('.main-nav a')];
const routes = [...document.querySelectorAll('.route')];

function showRoute(focusHeading) {
  const route = routes.find(section => '#' + section.id === location.hash) ?? routes[0];
  for (const section of routes) section.hidden = section !== route;
  for (const link of links) {
    if (link.hash === '#' + route.id) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  if (focusHeading) {
    window.scrollTo(0, 0);
    route.querySelector('h1').focus({ preventScroll: true });
  }
}

showRoute(false);
window.addEventListener('hashchange', () => {
  if (location.hash !== '#main') showRoute(true);
});
document.querySelector('.skip-link').addEventListener('click', event => {
  event.preventDefault();
  document.querySelector('#main').focus();
});

mountExperience(document.querySelector('#play-intro'));
mountMarkets(document.querySelector('#cot-content'), document.querySelector('#retail-content'));
