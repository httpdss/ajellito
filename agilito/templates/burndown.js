    <script type="text/javascript" language="javascript">
        function burndown(div, ticks) {
            ideal = [ {{ burndown.remaining.ideal|join:"," }} ];
            hours = [ {{ burndown.remaining.hours|join:"," }} ];
            storypoints = [ {{ burndown.remaining.points|join:"," }} ];

            plot1 = $.jqplot(div, [ideal, storypoints, hours], {
                // title:'Burndown',
                legend:{show:true, location:'sw'},
                series:[
                    {label: 'Ideal', yaxis: 'yaxis'},
                    {label: 'Points', yaxis:'y2axis'},
                    {label: 'Hours', yaxis: 'yaxis'}
                    ],
                axes:{
                    xaxis:{min:1, max:{{burndown.days}}, tickInterval:1, tickOptions:{formatString:'%d'}}, 
                    yaxis:{min:0, max:{{burndown.max.hours}} * 1.01, tickOptions:{formatString:'%d'}}, 
                    y2axis:{min:0, max:{{burndown.max.points}} * 1.01, tickOptions:{formatString:'%d'}}
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
