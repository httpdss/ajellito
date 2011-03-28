    <script type="text/javascript" language="javascript">
        function burndown(div) {
            ideal = [ {{ burndown.remaining.ideal|join:"," }} ];
            hours = [ {{ burndown.remaining.hours|join:"," }} ];
            storypoints = [ {{ burndown.remaining.points|join:"," }} ];
            xticks = [ {% for x, label in burndown.labels %}{% if not forloop.first %}, {% endif %}[{{x|add:"1"}}, '{{label|addslashes}}']{% endfor %}];

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
                    // xaxis:{min:1, max:{{burndown.days}}, tickInterval:1, tickOptions:{formatString:'%d'}}, 
                    xaxis:{min:1, max:{{burndown.days|default:0}}, tickInterval:1, ticks:xticks}, 
                    y2axis:{min:0, max:{% if burndown.max.points %}{{burndown.max.points}} {% else %}1{% endif %}, tickOptions:{formatString:'%4.2f'}},
                    yaxis:{min:0, max:{% if burndown.max.hours %}{{burndown.max.hours}}{% else %}1{% endif %}, tickOptions:{formatString:'%4.2f'}}
                    },
                highlighter:{
                    tooltipAxes: 'y',
                    formatString: '%4.2f'
                }
            });
        }
    </script>
