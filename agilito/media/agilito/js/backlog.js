/*
update_us = function(){
    data = {"id":$(this).attr("id"),"name":$(this).attr("value")}

        $.ajax({
            type: "POST",
            url: "update_us/",
            data: data,
            success: function(msg){
                $(".user-story .us-title-edit").replaceWith("<a href='#' class='title'>"+data["name"]+"</a>")
                $("#" + data["id"]).css("background", "yellow").animate({backgroundColor: "#f0f0f0"}, 10000, "swing");                
        },
        error:function(){
            console.log("You took too much man, you took too much")
        }
    });
    
    
}
*/

update_us = function(nodeid){
    //We'll capture the submit event and make and ajax post
    //append to list

    uscontainer = $(nodeid)
    usform = uscontainer.find('#us-form')
    data = usform.serialize() 
    url = usform.attr('action')
    $.ajax({
        type: "POST",
        url: url,
        data: data,
        success: function(msg){
            ret = $(msg);
            
            if (ret.find("div.user-story").length == 0) {
                charge_form(msg, nodeid);
            } else {
                uslist = $(nodeid).parents("li");
                uslist.empty()
                uslist.append(msg);
                uslist.find(".collapse-controls").click(toggle_collapse);
                uslist.find(".user-story .edit").click(edit_us);


                uslist.find(".user-story").css("background", "yellow")
                                         .animate({backgroundColor: "#f0f0f0"}, 3000, "swing");
                
            }
        },
        error:function(){
            console.log("There is an error trying to load "+url)
        }
    });

    return false;
}


edit_us = function() {
    us_copy = $(this).parents(".user-story")
    nodeid = $(this).parents("li")
    url = $(this).attr("href")
    $.ajax({
        url: url,
        data: {},
        success: function(msg) {
            usnew = $(nodeid)
            usnew.empty().append(msg)
                
            usnew.find("#us-cancel").click(function() {
                            usnew.append(us_copy)
                            nodeid.find("#us-form").remove()
            });
            usnew.find("#us-form").submit(function() {update_us(nodeid);return false;});
            usnew.find(".collapse-controls").click(toggle_collapse);
            usnew.find(".edit").click(edit_us);
            
            usnew.css("display","block")
          
        },
        error:function(){
            console.log("There is an error trying to load "+url)
        }
    });      
    return false;
}

new_us = function(nodeid){
    //We'll capture the submit event and make and ajax post
    //append to list
    uscontainer = $(nodeid)
    usform = uscontainer.find('#us-form')
    data = usform.serialize() 
    url = usform.attr('action')
    $.ajax({
        type: "POST",
        url: url,
        data: data,
        success: function(msg){
            ret = $(msg);
            
            if (ret.find("div.user-story").length == 0) {
                charge_form(msg, nodeid);
            } else {
                uslist = $("#user-story-list");
                uslist.append(msg);
                uslist.find(".collapse-controls").click(toggle_collapse);
                uslist.find(".user-story .edit").click();


                $("#user-story-list div.user-story:last").css("background", "yellow")
                                                          .animate({backgroundColor: "#f0f0f0"}, 3000, "swing");
                uscontainer.empty().css("display","none");
            }
        },
        error:function(){
            console.log("There is an error trying to load "+url)
        }
    });

    return false;
}

load_form = function(nodeid, url){
    $.ajax({
        url: url,
        data: {},
        success: function(msg) {
            charge_form(msg, nodeid)
        },
        error:function(){
            console.log("There is an error trying to load "+url)
        }
    });
}

charge_form = function(msg, nodeid) {
    usnew = $(nodeid)
    usnew.empty().append(msg)
        
    usnew.find("#us-cancel").click(function() {usnew.css("display","none")});
    usnew.find("#us-form").submit(function() {new_us(nodeid);return false;});
    
    usnew.css("display","inline")
}


$(document).ready(function(){
    //First we hide some things
    $(".user-story .details").hide()
    $(".us-collapse").css("display","none")
    
    $("#us-form :text").attr("value", " ")
    $("#us-form textarea").attr("value", " ")


    $("#create-user-story").click(function(){
        //$("#us-new").css("display","inline")
        //$("#us-form").submit(function() {new_us("#us-new")})
        load_form("#us-new","short_us_form/")
    })

    $("#create-detailed-user-story").click(function() {
        load_form("#us-new","detailed_us_form/")
    });

    $(".user-story .edit").click(edit_us);

    /*$("#us-cancel").click(function(){
        $("#us-new").css("display","none")
    })*/
    /*
    $(".user-story .title").click(function(){
        value = $(this).find(".us-name").text()
        us_id = $(this).attr("id")
        
        $(this).replaceWith("<input type='text' id='"+us_id+"' class='us-title-edit' style='width:40em' value='"+value+"' />")
        $(".user-story .us-title-edit").blur(update_us)
        $(".user-story .us-title-edit").keypress(function (e) {
            console.log("Key pressed: " + e.which)
          if (e.which == 13) {
            update_us()
          }
        });
        
    })
    */
    
})



      

  

