import React from 'react';
import classNames from 'classnames';
import { H5, Icon, Popover } from "@blueprintjs/core";

export default function SectionHeader (props) {
    const className = classNames(
        'flex items-center b--black-10', props.fontSize || 'f4', {'bb': props.border}
    );
    return (
        <div className={className}>
            <div className='pr2'>{props.title}</div>
            <Popover>
                <Icon icon='info-sign' iconSize={12} color='#bbb' style={{marginTop: '-2px'}}/>
                {props.popoverContent}
            </Popover>
        </div>
    );
}
