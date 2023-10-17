import "./style.css";
import { NightVision } from "night-vision";
import { DataLoader } from "./dataLoader.js";
import wsx from "./wsx.js";
import sampler from "./ohlcvSampler.js";

document.querySelector("#app").innerHTML = `
<style>
body {
    background-color: #0c0d0e;
}
</style>
<h1>Night Vision Charts</h1>
<div id="chart-container"></div>
`;
let chart = new NightVision("chart-container", {});

let dl = new DataLoader();

// Load the first piece of the data
dl.load((data) => {
  chart.data = data; // Set the initial data
  chart.fullReset(); // Reset tre time-range
  chart.se.uploadAndExec(); // Upload & exec scripts
});

function loadMore() {
  let data = chart.hub.mainOv.data;
  let t0 = data[0][0];
  if (chart.range[0] < t0) {
    dl.loadMore(t0 - 1, (chunk) => {
      // Add a new chunk at the beginning
      data.unshift(...chunk);
      // Yo need to update "data"
      // when the data range is changed
      chart.update("data");
      chart.se.uploadAndExec();
    });
  }
}

// Send an update to the script engine
async function update() {
  await chart.se.updateData();
  var delay; // Floating update rate
  if (chart.hub.mainOv.dataSubset.length < 1000) {
    delay = 10;
  } else {
    delay = 1000;
  }
  setTimeout(update, delay);
}

// Load new data when user scrolls left
chart.events.on("app:$range-update", loadMore);

// Plus check for updates every second
setInterval(loadMore, 500);

// TA + chart update loop
setTimeout(update, 0);

// Setup a trade data stream
wsx.init([dl.SYM]);
wsx.ontrades = (d) => {
  if (!chart.hub.mainOv) return;
  let data = chart.hub.mainOv.data;
  let trade = {
    price: d.price,
    volume: d.price * d.size,
  };
  if (sampler(data, trade)) {
    chart.update("data"); // New candle
    chart.scroll(); // Scroll forward
  }
};
window.wsx = wsx;
