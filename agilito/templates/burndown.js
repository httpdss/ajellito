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
            ideal = [ {{ burndown.remaining.ideal|join:"," }} ];
            hours = [ {{ burndown.remaining.hours|join:"," }} ];
            storypoints = [ {{ burndown.remaining.points|join:"," }} ];
            xticks = range({{burndown.days}}, Math.ceil(({{burndown.days}} + 1) / 2));
            yticks = range({{burndown.max.hours}}, ticks);
            y2ticks = range({{burndown.max.points}}, ticks);

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
            
            $('#' + div + ' .jqplot-legend div div').each(function(i) {
                $(this).append('<div></div>');
                $(this).find('div').css('border-top', '7px solid ' + $(this).css('background-color'));
            });
        }
    </script>
