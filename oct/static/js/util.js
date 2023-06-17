import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";
const difficultyColourSpectrum = d3.scaleLinear()
  .domain([0.1, 1.25, 2, 2.5, 3.3, 4.2, 4.9, 5.8, 6.7, 7.7, 9])
  .clamp(true)
  .range(['#4290FB', '#4FC0FF', '#4FFFD5', '#7CFF4F', '#F6F05C', '#FF8068', '#FF4E6F', '#C645B8', '#6563DE', '#18158E', '#000000'])
  .interpolate(d3.interpolateRgb.gamma(2.2));


export function getDiffColor(starRating) {
	if (starRating < 0.1) return "#AAAAAA";
	if (starRating >= 9) return "#000000";
	return difficultyColourSpectrum(starRating);
}