    <script type="text/javascript" language="javascript">
  
        function range(top, nticks)
        {
            delta = Math.ceil(top/nticks);

            ticks = new Array();
            for (t = 0; t <= nticks; t++) {
                ticks.push(t * delta);
            }

            return ticks;
        }

        function burndown(div, ticks) {
            ideal = [ {{ burndown.ideal|join:"," }} ];
            hours = [ {{ burndown.remaining|join:"," }} ];
            storypoints = [ {{ burndown.remaining_storypoints|join:"," }} ];
            xticks = range({{burndown.ideal|length}}, Math.ceil(({{burndown.ideal|length}} + 1) / 2));
            yticks = range({{burndown.y_max}}, ticks);
            y2ticks = range({{burndown.y2_max}}, ticks);

            plot1 = $.jqplot(div, [ideal, storypoints, hours], {
                // title:'Burndown',
                legend:{show:true, location:'sw'},
                series:[
                    {label: 'Ideal', yaxis: 'yaxis'},
                    {label: 'Points', yaxis:'y2axis'},
                    {label: 'Hours', yaxis: 'yaxis'}
                    ],
                axes:{
                    xaxis:{ticks:xticks, tickOptions:{formatString:'%d'}}, 
                    yaxis:{ticks:yticks, tickOptions:{formatString:'%d'}}, 
                    y2axis:{ticks:y2ticks, tickOptions:{formatString:'%d'}}
                    },
                highlighter:{
                    tooltipAxes: 'y',
                    formatString: '%s'
                }
            });
        }
    </script>
