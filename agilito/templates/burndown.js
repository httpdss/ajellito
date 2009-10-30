    <script type="text/javascript" language="javascript">
        function burndown(div) {
            ideal = [ {{ burndown.remaining.ideal|join:"," }} ];
            hours = [ {{ burndown.remaining.hours|join:"," }} ];
            storypoints = [ {{ burndown.remaining.points|join:"," }} ];

            // jqplot currently can't handle series that have all the
            // same datapoints
            p = storypoints[0];
            bug = true;
            for (i in storypoints) {
                if (storypoints[i] != p) {
                    bug = false;
                    break;
                }
            }
            if (bug) {
                storypoints = hours.slice();
                pmax = {{burndown.max.hours}};
            } else {
                pmax = {{burndown.max.points}};
            }

            plot1 = $.jqplot(div, [ideal, storypoints, hours], {
                legend:{show:true, location:'sw'},
                grid:{shadow:false},
                seriesDefault:{shadow:false},
                series:[
                    {label: 'Ideal', yaxis: 'yaxis'},
                    {label: 'Points', yaxis:'y2axis'},
                    {label: 'Hours', yaxis: 'yaxis'}
                    ],
                axes:{
                    xaxis:{min:1, max:{{burndown.days}}, tickInterval:1, tickOptions:{formatString:'%d'}}, 
                    y2axis:{min:0, max:pmax * 1.01, tickOptions:{formatString:'%d'}},
                    yaxis:{min:0, max:{{burndown.max.hours}} * 1.01, tickOptions:{formatString:'%d'}}
                    },
                highlighter:{
                    tooltipAxes: 'y',
                    formatString: '%s'
                }
            });
            
            /* $('#' + div + ' .jqplot-legend div div').each(function(i) {
                $(this).append('<div></div>');
                $(this).find('div').css('border-top', '7px solid ' + $(this).css('background-color'));
            }); */
        }
    </script>
