// SCROLL WITH ARROWS ON DESKTOP

document.addEventListener('keydown', function(event) {
    // FIND CLOSET LINE TO TOP
    const container = document.querySelector('.cards-container');
    const rows = Array.from(container.children);
    let activeRow = -1;
    let closestRowDifference = Infinity;
    rows.forEach((row, index) => {
        const rect = row.getBoundingClientRect();
        const difference = Math.abs(rect.top);
        if (difference < closestRowDifference) {
            closestRowDifference = difference;
            activeRow = index;
        }
    });
    if (activeRow == -1) { return }

    // UP & DOWN
    if (event.key === 'ArrowDown') {
        if (activeRow < rows.length - 1) {
            rows[activeRow + 1].scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    if (event.key === 'ArrowUp') {
        if (activeRow > 0) {
            rows[activeRow - 1].scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    // LEFT & RIGHT
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
        console.log("Active", activeRow);
        const activeCards = Array.from(rows[activeRow].children);

        // FIND CLOSET CARD TO LEFT
        let activeCard = -1;
        let closestCardDifference = Infinity;
        activeCards.forEach((card, index) => {
            const rect = card.getBoundingClientRect();
            const difference = Math.abs(rect.left - container.getBoundingClientRect().left);
            console.log(activeRow, rect.left);
            if (difference < closestCardDifference) {
                closestCardDifference = difference;
                activeCard = index;
            }
        });
        if (activeCard == -1) { return }

        if (event.key === 'ArrowRight' && activeCard < activeCards.length - 1) {
            console.log("RIGHT", activeRow, activeCard, activeCards[activeCard].innerHTML);
            activeCards[activeCard + 1].scrollIntoView({ behavior: 'smooth', inline: 'center' });
        } else if (event.key === 'ArowLeft' && activeCard > 0) {
            console.log("LEFT", activeRow, activeCard, activeCards[activeCard].innerHTML);
            activeCards[activeCard - 1].scrollIntoView({ behavior: 'smooth', inline: 'center' });
        }
    }
});