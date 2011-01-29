toggle_collapse = function(){
    //We check if the state of the collapse button
    //XXX: We could have used $.toggle but it pollutes the dom with stuff that we don't want and behaves strangely
    if ($(this).find(".us-collapse").css("display")=='none'){        
        $(this).find(".us-expand").css("display","none")
        $(this).find(".us-collapse").css("display","inline")
        $(this).parents("li").find(".details").css("display","block")
    }
    else if ($(this).find(".us-collapse").css("display")=='inline'){        
        $(this).find(".us-expand").css("display","inline")
        $(this).find(".us-collapse").css("display","none")
        $(this).parents("li").find(".details").css("display","none")
    }

    return false;
}

$(document).ready(function(){
    $(".collapse-controls").click(toggle_collapse)
})
