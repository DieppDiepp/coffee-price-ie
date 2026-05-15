declare module 'plotly.js-dist-min' {
  const Plotly: any;
  export = Plotly;
}

declare module 'react-plotly.js/factory' {
  const createPlotlyComponent: (plotly: any) => React.ComponentType<any>;
  export = createPlotlyComponent;
}
