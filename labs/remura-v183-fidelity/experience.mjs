const frames = Array.from({ length: 9 }, (_, index) =>
  new URL(`./assets/experience/frame-${index}.webp`, import.meta.url).href
);
const logo = new URL("./assets/experience/smf.webp", import.meta.url).href;
const durations = [300, 300, 300, 300, 300, 450, 420, 420, 3000];

export function mountExperience(trigger = document.getElementById("play-intro")) {
  if (!trigger) return;

  const dialog = document.createElement("dialog");
  if (typeof dialog.showModal !== "function") {
    trigger.hidden = true;
    return;
  }

  dialog.id = "intro";
  dialog.setAttribute("aria-labelledby", "intro-title");
  dialog.innerHTML = `
    <div class="intro-experience">
      <h2 id="intro-title">Introduzione REMURA</h2>
      <div class="intro-scene" aria-hidden="true"></div>
      <div class="intro-flash" aria-hidden="true"></div>
      <p class="intro-loading" role="status"></p>
      <div class="intro-credits" hidden>
        <img alt="Logo SMF" width="64" height="64">
        <p>Un ringraziamento speciale a SMF per il prezioso contributo allo sviluppo e alla ricerca di REMURA.</p>
      </div>
      <button class="intro-skip" type="button" autofocus>Salta introduzione</button>
    </div>`;

  const scene = dialog.querySelector(".intro-scene");
  const loading = dialog.querySelector(".intro-loading");
  const credits = dialog.querySelector(".intro-credits");
  const creditsLogo = credits.querySelector("img");
  const skip = dialog.querySelector(".intro-skip");
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  let playback = 0;
  let timer;
  let failSafe;
  let returnFocus = true;

  function stop() {
    playback++;
    clearTimeout(timer);
    clearTimeout(failSafe);
  }

  function showFrame(images, index, run) {
    if (run !== playback || !dialog.open) return;

    images.forEach((image, frame) => {
      image.classList.toggle("visible", frame === index);
    });
    dialog.dataset.phase = index === 5 ? "collision" : index >= 6 ? "reveal" : "battle";
    credits.hidden = index < 6;
    timer = setTimeout(() => {
      if (index + 1 < images.length) showFrame(images, index + 1, run);
      else dialog.close();
    }, durations[index]);
  }

  async function open({auto=false}={}) {
    if (dialog.open) return;

    returnFocus = !auto;
    const run = ++playback;
    const staticView = reducedMotion.matches;
    const images = (staticView ? frames.slice(-1) : frames).map((path) => {
      const image = new Image();
      image.alt = "";
      image.src = path;
      return image;
    });
    creditsLogo.src = logo;
    scene.replaceChildren(...images);
    credits.hidden = true;
    dialog.dataset.phase = "loading";
    loading.textContent = "Caricamento introduzione…";
    skip.textContent = staticView ? "Chiudi introduzione" : "Salta introduzione";
    dialog.showModal();
    failSafe=setTimeout(()=>{if(dialog.open && run===playback)dialog.close();},12000);
    skip.focus();

    try {
      await Promise.all([...images, creditsLogo].map((image) => image.decode()));
    } catch {
      if (run === playback && dialog.open) dialog.close();
      return;
    }

    if (run !== playback || !dialog.open) return;
    loading.textContent = "";
    if (staticView) {
      dialog.dataset.phase = "reveal";
      images[0].classList.add("visible");
      credits.hidden = false;
      clearTimeout(failSafe);
      return;
    }

    showFrame(images, 0, run);
  }

  document.body.append(dialog);
  skip.addEventListener("click", () => dialog.close());
  dialog.addEventListener("cancel", stop);
  dialog.addEventListener("close", () => {
    if (dialog.open) return;
    stop();
    if(returnFocus)trigger.focus();
  });
  reducedMotion.addEventListener("change", () => {
    if (dialog.open && reducedMotion.matches) dialog.close();
  });
  trigger.addEventListener("click", () => open());
  trigger.hidden = false;
  return {open};
}
